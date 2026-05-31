import sys
from urllib3 import PoolManager
from bs4 import BeautifulSoup
import json
import time
import random
import clean

basePageURL = 'https://www.thegradcafe.com/survey?page='
basePageURLSortOrder = '&sort=newest'
baseURL = 'https://www.thegradcafe.com'
http = PoolManager()

sourceCols = [
        "page",
        "html"
    ]

def _newSourceRecord():
    return dict.fromkeys(sourceCols, "")

def _fetchPage(pageNum):
    # Build in wait time for politeness
    time.sleep(random.randint(0,5))
    
    url = basePageURL + str(pageNum) + basePageURLSortOrder
    response = http.request('GET', url)
    status = response.status

    if status != 200:
        if status == 400:
            print("Bad Request on Base Page")
        elif status == 404:
            print("Base Page not found")
        else:
            print(f"An unexpected HTTP result was returned: {status}")
        sys.exit(1)
    return response.data

def scrape_data():
    
    # 30,000 entries at 20 Entries per page is 1500 pages
    numPagesToRead = 1
    #currentPage = 1

    cleanData = list()
    sourceData = list()

    for page in range(1, numPagesToRead+1):
        parsedPage = BeautifulSoup(_fetchPage(page), "html.parser")

        tableBody = parsedPage.find("tbody")
        tableRows = tableBody.find_all("tr")
        #cleanData.append(clean.clean_data(tableRows))
        cleanData = cleanData + clean.clean_data(tableRows)

        pageSource = _newSourceRecord()
        pageSource["page"] = page
        pageSource["html"] = str(tableBody)
        sourceData.append(pageSource)

        print(f"Completed Page: {page}")

    clean.save_data(cleanData, "applicant_data.json")
    clean.save_data(sourceData, "source_html.json")

    return cleanData

def load_data(fileName):
    with open(fileName, 'r') as f:
        return json.load(f)