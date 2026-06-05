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

    if status == 200:
        return response.data, status
    elif status == 500:
        # Internal server error, lets wait a little bit and retry
        time.sleep(5)
        return _fetchPage(pageNum)
    elif status == 400:
        # Bad request, exit
        print("Bad Request on Base Page")
        sys.exit(1)
    elif status == 404:
        # Exit if no page found
        print("Base Page not found")
        sys.exit(1)
    else:
        print(f"An unexpected HTTP result was returned: {status}")
        sys.exit(1)
    

def scrape_data():
    
    # 50,000 entries at 20 Entries per page is 2500 pages
    numPagesToRead = 2500
    #currentPage = 1

    cleanData = list()
    sourceData = list()

    for page in range(1, numPagesToRead+1):
        start = time.time()
        content, status = _fetchPage(page)
        parsedPage = BeautifulSoup(content, "html.parser")
        print(f"Page returned status: {status}")

        tableBody = parsedPage.find("tbody")
        tableRows = tableBody.find_all("tr")
        #cleanData.append(clean.clean_data(tableRows))
        cleanData = cleanData + clean.clean_data(tableRows)

        pageSource = _newSourceRecord()
        pageSource["page"] = page
        pageSource["html"] = str(tableBody)
        sourceData.append(pageSource)

        end = time.time()
        timeDif = end - start
        print(f"Completed Page: {page}, Parse Time: {timeDif}s")

    clean.save_data(cleanData, "applicant_data.json")
    clean.save_data(sourceData, "source_html.json")

    return cleanData

def load_data(fileName):
    with open(fileName, 'r') as f:
        return json.load(f)