"""
A LangChain Tool for retrieving legal opinions from Google Scholar.
"""
import os
import random
import requests
import sys
import undetected_chromedriver as uc
import logging
from contextlib import ExitStack
from fp.fp import FreeProxy
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from tqdm import tqdm


PROXY_FILE = 'proxies.cfg'
logging.basicConfig(level=logging.INFO)


def load_proxies():
    if os.path.isfile(PROXY_FILE):
        with open(PROXY_FILE, 'r') as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []


def save_proxies(proxies):
    with open(PROXY_FILE, 'w') as f:
        f.write('\n'.join(proxies))


def setup_driver(proxy=None):
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')
    return uc.Chrome(options=options)


def reset_proxy(proxies):
    while proxies:
        proxy = random.choice(proxies)
        proxies.remove(proxy)
        try:
            response = requests.get("http://httpbin.org/ip", proxies={"http": proxy, "https": proxy}, timeout=5)
            if response.status_code == 200:
                logging.info(f'Using proxy: {proxy}')
                return setup_driver(proxy), proxy
        except:
            logging.warning(f"Proxy {proxy} failed, trying another one.")

    logging.info("No valid proxy in the list, attempting to fetch a new proxy from FreeProxy.")
    while True:
        proxy = FreeProxy(rand=True, timeout=1, https=True).get()
        if proxy:
            logging.info(f'Using FreeProxy: {proxy}')
            return setup_driver(proxy), proxy
        logging.warning("FreeProxy failed, trying again...")

def safe_get(driver, url, proxy, proxies, links):
    while True:
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h3.gs_rt a')))
            links.extend([link.get_attribute('href') for link in driver.find_elements(By.CSS_SELECTOR, 'h3.gs_rt a') if 'https://scholar' in link.get_attribute('href')])
            if not links:
                logging.warning('No legal opinion links found. Resetting proxy.')
                raise Exception('No legal opinion links found.')
            url = get_next_url(driver)
            return links, url, proxy
        except Exception as e:
            logging.error(f'An error occurred with: {proxy}. Error: {e}. Resetting proxy.')
            if proxy in proxies:
                proxies.remove(proxy)
            save_proxies(proxies)
            driver.quit()
            driver, proxy = reset_proxy(proxies)
            if proxy and proxy not in proxies:
                proxies.append(proxy)
                save_proxies(proxies)


def get_next_url(driver):
    try:
        next_button_container = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'gs_n')))
        next_button = next_button_container.find_element(By.CSS_SELECTOR, 'span.gs_ico_nav_next')
        if next_button.is_enabled() and next_button.is_displayed():
            next_button.click()
            return driver.current_url
        else:
            logging.warning("Next page button not found or not clickable. No more pages to traverse.")
            return None
    except NoSuchElementException:
        logging.warning("No next page button found.")
        return None
    except Exception as e:
        logging.error(f"An error occurred while getting the next url: {e}")
        return None
 

def fetch_and_save_opinions(links, save_dir, court_string):
    progress_bar = tqdm(total=len(links), ncols=75)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    proxies = load_proxies()
    driver = setup_driver()
    if driver is None:
        logging.error("Unable to set up a driver. Exiting.")
        return
    try:
        for link in links:
            while True:
                try:
                    driver.get(link)
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    opinion_div = soup.find('div', id='gs_opinion')
                    if opinion_div:
                        break
                    else:
                        raise WebDriverException("Failed to retrieve opinion div, changing proxy...")
                except WebDriverException:
                    logging.warning("Failed to establish a connection or failed to retrieve opinion div, trying a new proxy...")
                    if driver:
                        driver.quit()
                    driver, proxy = reset_proxy(proxies)
                    if proxy and proxy not in proxies:
                        proxies.append(proxy)
                    continue

            text = '\n'.join(opinion_div.get_text(separator="\n").split('\n')[:-1])
            title = soup.find('h1', dir='ltr').text
            title = title.replace(',', '').replace(' ', '_').replace('/', '-').replace(':', '')
            file_name = os.path.join(save_dir, f"{title}.txt")
            with open(file_name, 'w') as f:
                f.write(text)
                progress_bar.update()
    finally:
        if driver:
            driver.quit()
    progress_bar.close()


def main(search_phrase, court, save_dir):
    url = f"https://scholar.google.com/scholar?hl=en&as_sdt={court}&q={quote_plus(search_phrase)}&btnG=&oq="
    proxies = load_proxies()
    driver = setup_driver()
    if driver is None:
        logging.error("Unable to set up a driver due to lack of valid proxies. Exiting.")
        return

    stack = ExitStack()
    stack.callback(driver.quit)
    stack.callback(save_proxies, proxies)

    links = []
    while url:
        links, url, proxy = safe_get(driver, url, None, proxies, links)
        logging.info(f'Fetched {len(links)} links so far with: {proxy if proxy else "local connection"}.')
        if not url:
            logging.info('No more Google Scholar search results pages. Done.')
            logging.info(f'Links: {links}')
            logging.info('Number of opinions: ' + str(len(links)))
    fetch_and_save_opinions(links, save_dir, court)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
