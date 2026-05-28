import sys
from urllib3 import PoolManager
from bs4 import BeautifulSoup


basePageURL = 'https://www.thegradcafe.com/survey?page='
basePageURLSortOrder = '&sort=newest'
baseURL = 'https://www.thegradcafe.com'

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
        "greaw"
    ]

def _newRecord():
    return dict.fromkeys(cols, "None")

def _processPrimaryRow(tr, tempDict):
    tableData = tr.find_all("td")
    # Row 1 field order = 0: University, 1: Degree Name and Type, 2: Date Added, 3: Status and Date of Status, 4: ID/URL
    
    # 0 University
    print(tableData[0].text)
    tempDict["university"] = str.strip(tableData[0].text)

    # 1 Degree Name and Type
    # Each element is in their own span tag
    spans = tableData[1].find_all("span")
    print(spans[0].text)
    print(spans[1].text)
    tempDict["program"] = str.strip(spans[0].text)
    tempDict["degree"] = str.strip(spans[1].text)

    # 2 Date added
    print(tableData[2].text)
    tempDict["date_added"] = str.strip(tableData[2].text)

    # 3 Statuses: Accepted, Rejected, Interview, Wait listed (Uniformity in the entry implies this is selected from a list)
    print(tableData[3].text)
    splitStatus = str.split(tableData[3].text, " on ")
    tempDict["status"] = str.strip(splitStatus[0])
    print(splitStatus[0])
    tempDict["status_date"] = str.strip(splitStatus[1])

    # 4 ID and specific URL
    # Located in anchor tag, so grab the "a" and read the href
    anchor = tableData[4].find("a")
    print(anchor["href"])
    tempDict["url"] = baseURL + anchor["href"]
    # We can pull out the ID so we have a unique identifier for later, so we might as well
    print("ID: " + str.split(anchor["href"], "/")[2])
    tempDict["id"] = str.split(anchor["href"], "/")[2]

def _processSecondaryRow(tr, tempDict):
    divs = tr.find_all("div")
    # 0 div sets up the flex grid for the row ** Skip it
    # 1 div repeats status info, but is hidden ** Skip it

    # 2 Term
    print(divs[2].text)
    tempDict["term"] = divs[2].text

    # 3 US or International
    print(divs[3].text)
    tempDict["US/International"] = divs[3].text

    # If there are no other flex boxes, exit
    if len(divs) == 4:
        return
    
    # Else the complicated parse
    for i in range(4, len(divs)):
        print(divs[i].text)
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
    
    numPagesToRead = 1
    currentPage = 1

    # Create connection pool manager
    http = PoolManager()
    url = basePageURL + str(currentPage) + basePageURLSortOrder
    print(url)

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

    parsedPage = BeautifulSoup(response.data, "html.parser")

    tableBody = parsedPage.find("tbody")
    #print(tableData)
    tableRows = tableBody.find_all("tr")

    tempDict = _newRecord()
    _processPrimaryRow(tableRows[0], tempDict)
    print(tempDict["id"])

    _processSecondaryRow(tableRows[1], tempDict)

    # Is there a third row with comments?
    p = tableRows[2].find("p")
    if len(p) == 1:
        print(p.text)
        tempDict["comments"] = p.text

    print(tempDict)
    

    
