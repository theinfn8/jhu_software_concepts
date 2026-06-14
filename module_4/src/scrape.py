from urllib3 import PoolManager
from bs4 import BeautifulSoup
import json
import time
import random
from src import clean

basePageURL = 'https://www.thegradcafe.com/survey?page='
basePageURLSortOrder = '&sort=newest'
baseURL = 'https://www.thegradcafe.com'
http = PoolManager()

sourceCols = [
        "page",
        "html"
    ]

def _fetchPage(pageNum):
    # Build in wait time for politeness
    time.sleep(random.randint(0,5))
    
    url = basePageURL + str(pageNum) + basePageURLSortOrder
    response = http.request('GET', url)
    status = response.status

    if status == 200:
        return response.data, status
    # Could cause an indefinite loop if the server is having major issues, rethink this and fix it
    # elif status == 500:
    #     # Internal server error, lets wait a little bit and retry
    #     time.sleep(5)
    #     return _fetchPage(pageNum)
    elif status == 400:
        # Bad request, exit
        print("Bad Request on Base Page")
        
    elif status == 404:
        # Exit if no page found
        print("Base Page not found")
        
    else:
        print(f"An unexpected HTTP result was returned: {status}")
        
    return response.data, status


def scrape_data(lastIDFetched):
    
    currentPage = 1

    cleanData = list()

    fetchMoreEntries = True

    while(fetchMoreEntries):
        content, status = _fetchPage(currentPage)

        if status != 200:
            return None
        
        parsedPage = BeautifulSoup(content, "html.parser")

        tableBody = parsedPage.find("tbody")
        tableRows = tableBody.find_all("tr")

        newCleanedData = clean.clean_data(tableRows, lastIDFetched)
        if newCleanedData == None:
            fetchMoreEntries = False
        else:
            if len(newCleanedData) < 20:
                fetchMoreEntries = False
            cleanData = cleanData + newCleanedData
        
        currentPage += 1

    return cleanData

def load_data(fileName):
    with open(fileName, 'r') as f:
        return json.load(f)