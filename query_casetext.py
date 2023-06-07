"""
A LangChain Tool for retrieving legal opinions from Casetext.
"""
import argparse
import os
import re
import time
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote_plus


def load_credentials(filepath='creds.txt'):
    """
    Load username and password from a text file.
    The text file should contain the username on the first line and the password on the second line.
    """
    if os.path.exists(filepath):
        with open(filepath, 'r') as file:
            username = file.readline().strip()
            password = file.readline().strip()
            return username, password
    return None, None


def log_in_to_casetext(driver, username, password):
    """
    Function to login to Casetext using undetected_chromedriver and Selenium.
    """
    driver.get('https://casetext.com')
    driver.find_element(By.XPATH, "//a[span[text()='Log in']]").click()
    time.sleep(3)  # let the login page load
    driver.find_element(By.ID, "email").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.XPATH, "//button[text()='Sign In']").click()
    time.sleep(3)  # let the home page load after login


def is_last_page(driver):
    """
    Function to check if current page is the last page of search results.
    """
    try:
        driver.find_element(By.XPATH, '//button[@aria-label="Go to next page"]')
        return False
    except NoSuchElementException:
        return True


def sanitize_filename(filename, max_length=255):
    """
    Function to sanitize the file name.
    """
    # Remove invalid characters
    filename = re.sub(r'[\\/*?:"<>|]', '', filename)

    # Replace apostrophes with underscores
    filename = filename.replace("'", "_").strip().replace(' ', '_')

    # Truncate to the maximum file length if necessary
    if len(filename) > max_length:
        filename = filename[:max_length - len('.txt')] + '.txt'

    return filename


def search_in_casetext(driver, search_phrase, page_number, search_type):
    """
    Function to search phrases in Casetext.
    """
    url = f"https://casetext.com/v2/search?jxs=fl&p={page_number}&publishedCasesOnly=true&q={quote_plus(search_phrase)}&sort={search_type}&type=case"
    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "ct-search-result-container")))
    except TimeoutException:
        # If the page doesn't load the results container in time,
        # it might be because it's the last page and there are no results.
        if is_last_page(driver):
            print('No more results found.')
            return None

    return url


def get_links_from_current_page(driver):
    """
    Function to get links from current page of search results.
    """
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    case_items = soup.find_all('div', {'class': 'ct-search-result-container'})

    links = {}
    for item in case_items:
        header = item.find('div', {'class': 'ct-search-result-header'})
        subheader = item.find('div', {'class': 'ct-search-result-subheader'})

        link = header.find('a', href=True)['href']
        title = header.find('a').text
        citation = subheader.find('span').text if subheader else ''

        file_name = sanitize_filename(title + ' ' + citation)
        links[file_name] = link

    return links


def save_opinion_text(driver, links, output_dir, search_url):
    """
    Function to save opinion text to files.
    """
    for filename, link in links.items():
        retries = 9
        for i in range(retries):
            try:
                driver.get(link)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "section.decision.opinion")))
                break
            except TimeoutException:
                if i < retries - 1:  # i is zero indexed
                    continue
                else:
                    raise

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Metadata extraction
        short_title = soup.find('h1', {'class': 'short-title'}).text if soup.find('h1', {'class': 'short-title'}) else 'NA'
        jurisdiction = soup.find('span', {'class': 'jurisdiction'}).text if soup.find('span', {'class': 'jurisdiction'}) else 'NA'
        decide_date = soup.find('span', {'class': 'decide-date'}).text if soup.find('span', {'class': 'decide-date'}) else 'NA'
        citation = soup.find('span', {'class': 'citation mt-1'}).text if soup.find('span', {'class': 'citation mt-1'}) else 'NA'
        docket = soup.find('p', {'class': 'docket'}).text if soup.find('p', {'class': 'docket'}) else 'NA'
        docket_date = soup.find('p', {'class': 'docDate'}).text if soup.find('p', {'class': 'docDate'}) else 'NA'
        caption = soup.find('p', {'class': 'caption'}).text if soup.find('p', {'class': 'caption'}) else 'NA'

        # Opinion text extraction
        opinion_section = soup.find('section', {'class': 'decision opinion'})
        if opinion_section:
            text = opinion_section.get_text(separator='\n', strip=True)  # get all text within the section
        else:
            print(f'No opinion text found for {filename}.')
            continue

        # Write metadata and opinion text to file
        with open(os.path.join(output_dir, filename + '.txt'), 'w', encoding='utf-8') as file:
            file.write(f'Short Title: {short_title}\nJurisdiction: {jurisdiction}\nDecide Date: {decide_date}\n')
            file.write(f'Citation: {citation}\nDocket: {docket}\nDocket Date: {docket_date}\nCaption: {caption}\n\n')
            file.write(text)
            print('Wrote ' + os.path.join(output_dir, filename + '.txt'))

        # Navigate back to the original search URL
        driver.get(search_url)


def main(search_phrase, output_dir, headless, search_type, max_pages, username, password):
    """
    Main function to run the script.
    """
    options = uc.ChromeOptions()
    if headless:
        options.add_argument('--headless')

    driver = uc.Chrome(options=options)

    log_in_to_casetext(driver, username, password)

    # Check if output_dir exists, if not, create it.
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    page_number = 1
    while True:
        search_url = search_in_casetext(driver, search_phrase, page_number, search_type)

        if search_url is None:
            print('Reached the end of results. Exiting...')
            break

        links = get_links_from_current_page(driver)
        save_opinion_text(driver, links, output_dir, search_url)

        # Check if we've reached the last page or the maximum page number, if so, break the loop
        if is_last_page(driver) or page_number >= max_pages:
            print('Reached the last page or maximum page number. Exiting...')
            break

        page_number += 1
    driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('search_phrase')
    parser.add_argument('output_dir')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--search_type', choices=['relevance', 'date-ascending', 'date-descending', 'cite-count'], default='relevance')
    parser.add_argument('--maxpage', type=int, default=float('inf'))
    parser.add_argument('--user', help="User name for casetext", default=None)
    parser.add_argument('--password', help="Password for casetext", default=None)
    args = parser.parse_args()

    username = args.user
    password = args.password

    # Load credentials from file if they're not provided as arguments
    if username is None or password is None:
        username, password = load_credentials()

    main(args.search_phrase, args.output_dir, args.headless, args.search_type, args.maxpage, username, password)
