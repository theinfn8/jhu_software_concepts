import sys
import scrape

# def _checkBotAllowed():
#     parser = robotparser.RobotFileParser()
#     parser.set_url("https://www.thegradcafe.com/robots.txt")
#     parser.read()

#     paths = ["/survey","/result/"]

#     for path in paths:
#         if not parser.can_fetch('cc', path):
#             print('Scraping of necessary page is not allowed')
#             sys.exit(1)

scrape.scrape_data()
#print('Scraping is ok!')

# basePageURL = 'https://www.thegradcafe.com/survey?page='
# sortOrderPageURL = '&sort=newest'
# baseResultURL = 'https://www.thegradcafe.com/result/'

# try:
#     response = request.urlopen(basePageURL)

# except error.HTTPError as err:
#     if err.code == 400:
#         print("Bad Request on Base Page")
#     if err.code == 404:
#         print("Base Page not found")

#     else:
#          print(f"An HTTP error has occured: {err}")

#     exit


# tableData = find_all("tbody")
# tableRows = tableData.find_all("tr")

# for row in tableRows:
# 	tableData = row.find_all("td")