import sys
from urllib3 import PoolManager
from bs4 import BeautifulSoup
import json
import time
import random

basePageURL = 'https://www.thegradcafe.com/survey?page='
basePageURLSortOrder = '&sort=newest'
baseURL = 'https://www.thegradcafe.com'
http = PoolManager()

cols = [
        "id",
        "program",
        "university",
        "comments",
        "date_added",
        "url",
        "status",
        "status_date",
        "accepted",
        "rejected",
        "term",
        "US/International",
        "degree",
        "gpa",
        "gre",
        "grev",
        "greaw",
        "html_orig1",
        "html_orig2",
        "html_orig3"
    ]

def _newRecord():
    return dict.fromkeys(cols, "None")

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
            print(f"An HTTP error has occured: {status}")
        sys.exit(1)
    return response.data

def _processPrimaryRow(tr, tempDict):
    tableData = tr.find_all("td")
    # Row 1 field order = 0: University, 1: Degree Name and Type, 2: Date Added, 3: Status and Date of Status, 4: ID/URL
    
    # 0 University
    tempDict["university"] = str.strip(tableData[0].text)

    # 1 Degree Name and Type
    # Each element is in their own span tag
    spans = tableData[1].find_all("span")
    tempDict["program"] = str.strip(spans[0].text)
    tempDict["degree"] = str.strip(spans[1].text)

    # 2 Date added
    tempDict["date_added"] = str.strip(tableData[2].text)

    # 3 Statuses: Accepted, Rejected, Interview, Wait listed (Uniformity in the entry implies this is selected from a list)
    splitStatus = str.split(tableData[3].text, " on ")
    tempDict["status"] = str.strip(splitStatus[0])
    tempDict["status_date"] = str.strip(splitStatus[1])

    # 4 ID and specific URL
    # Located in anchor tag, so grab the "a" and read the href
    anchor = tableData[4].find("a")
    tempDict["url"] = baseURL + anchor["href"]
    # We can pull out the ID so we have a unique identifier for later, so we might as well
    tempDict["id"] = str.split(anchor["href"], "/")[2]

def _processSecondaryRow(tr, tempDict):
    divs = tr.find_all("div")
    # 0 div sets up the flex grid for the row ** Skip it
    # 1 div repeats status info, but is hidden ** Skip it

    # 2 Term
    tempDict["term"] = divs[2].text

    # 3 US or International
    tempDict["US/International"] = divs[3].text

    # If there are no other flex boxes, exit
    if len(divs) == 4:
        return
    
    # Else the complicated parse
    for i in range(4, len(divs)):
        parsedBox = str.split(divs[i].text)

        # If we have two items it should be GPA or GRE
        if len(parsedBox) == 2:
            if parsedBox[0] == 'GPA':
                # Got a GPA
                tempDict["gpa"] = parsedBox[1]
            elif parsedBox[0] == 'GRE':
                # Got the regular GRE
                tempDict["gre"] = parsedBox[1]

        # If we have three items, it's one of the other GREs
        elif len(parsedBox) == 3:
            if parsedBox[1] == 'V':
                tempDict["grev"] = parsedBox[2]
            if parsedBox[1] == 'AW':
                tempDict["greaw"] = parsedBox[2]


def scrape_data():
    
    # 30,000 entries at 20 Entries per page is 1500 pages
    numPagesToRead = 5
    #currentPage = 1

    data = list()

    for page in range(1, numPagesToRead):
        print("Page: {page}")
        parsedPage = BeautifulSoup(_fetchPage(page), "html.parser")

        tableBody = parsedPage.find("tbody")
        tableRows = tableBody.find_all("tr")

        i = 0
        entryCount = 0
        while i < len(tableRows):
            # Skip ad rows halfway through
            if entryCount == 10:
                i += 2

            tempDict = _newRecord()
            _processPrimaryRow(tableRows[i], tempDict)
            tempDict["html_orig1"] = str(tableRows[i].contents)
            i += 1

            _processSecondaryRow(tableRows[i], tempDict)
            tempDict["html_orig2"] = str(tableRows[i].contents)
            i += 1

            # Is there a third row with comments?
            p = tableRows[i].find("p")
            if p != None:
                tempDict["comments"] = p.text
                tempDict["html_orig3"] = str(tableRows[i].contents)
                i += 1

            data.append(tempDict)

            
            entryCount += 1
            
            # And skip the last ad row
            if entryCount == 20:
                i += 1

        

    with open("applicant_data.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(data))

    
