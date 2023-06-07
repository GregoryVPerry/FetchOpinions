# FetchOpinions 🎉🇺🇸🥳 - LangChain Tools for Legal Opinion Retrieval 

Tools to conduct comprehensive searches on [Casetext](https://casetext.com/) and [Google Scholar](https://scholar.google.com), legal research websites. Leverages Selenium and BeautifulSoup to navigate the sites, perform searches, and retrieve the text of search results with embedded metadata related to each opinion.

## Overview

The primary purpose of this toolset is to generate legal document corpora, which can then be used for vector similarity search applications. By using LangText, users can create a dataset of legal opinions and decisions that can be used to train machine learning models and build vector search systems. LangText is intended to be integrated in an autonomous fashion with [LangChain](https://github.com/hwchase17/langchain), for purposes of populating prompt-specific legal opinion embeddings within high performance vector textual similarity search databases. This in turn facilitates searching and retrieval of a user's documents, for automatic context prepending of LLM conversational interactions to facilitate downstream tasks such as automated legal pleading generation, motion practice guidance, legal opinion summarization, case corpora question answering, etc.

One unique application of these tools is to enhance the performance of large language models like GPT-3 or GPT-4. By prepending prompts with relevant documents specific to the context of user interactions, it's possible to provide temporal, current memory to LLM interactions, despite GPT-4's training cutoff date, which is particularly useful in continuing conversations or in the use of generative chat models such as ChatGPT-4.

## Usage

To use these scripts, you'll need to install several Python libraries including Selenium, BeautifulSoup and undetected_chromedriver. You can install these libraries using pip:

```pip3 install selenium beautifulsoup4 undetected_chromedriver```

You'll also need to have Chrome browser installed, as these tools use Headless Chrome for legal opinion retrievals.

You can run the Casetext scripts from the command line with the following syntax:

```python3 query_casetext.py "search phrase" output_dir [--headless] [--search_type {relevance, date-ascending, date-descending, cite-count}] [--maxpage MAXPAGE] [--user USER] [--password PASSWORD]```

Casetext credentials can be optionally stored in creds.txt, with the first line being the Casetext username and second line the user's password. Credentials are not required for Google Scholar searching.

## Options

- `search_phrase`: The phrase to search for on Casetext.
- `output_dir`: The directory where the opinions should be saved.
- `--headless`: Run in Headless Chrome (the browser won't be displayed).
- `--search_type`: Determines the sorting of search results. Options are 'relevance', 'date-ascending', 'date-descending', 'cite-count'. Default is 'relevance'.
- `--maxpage`: The maximum number of pages to analyze for search results. Default is to process all available pages.
- `--user`: Username for Casetext account.
- `--password`: Password for Casetext account.

If `--user` and `--password` are not provided, the script will attempt to load them from a `creds.txt` file in the same directory. The `creds.txt` file should contain the username on the first line and the password on the second line.

## Examples
```
# retrieve all Casetext results, headless mode, search type == cite count
python3 query_casetext.py "tortious interference contract" opinions/state/tortious_interference_contract --headless --search_type cite-count

# retrieve just the first 20 results (two pages) from Casetext, interactive browser mode, default search == relevance
python3 query_casetext.py "negligent hiring" opinions/state/negligent_hiring --maxpage 2
```
