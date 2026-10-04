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
    """
    Fetch a single paginated results page from GradCafe with a polite
    random delay.

    Constructs the target URL by interpolating ``pageNum`` between the
    module-level ``basePageURL`` and ``basePageURLSortOrder`` constants,
    issues an HTTP GET request via the module-level ``http`` pool
    manager, and returns the raw response body and status code.

    A random delay of 0–5 seconds is applied before each request to
    avoid overwhelming the source server.

    **URL construction:**

    .. code-block:: text

        https://www.thegradcafe.com/survey?page={pageNum}&sort=newest

    **HTTP status handling:**

    +--------+-------------------+-----------------------------------------------+
    | Status | Condition         | Behaviour                                     |
    +========+===================+===============================================+
    | 200    | OK                | Returns ``(response.data, 200)``              |
    +--------+-------------------+-----------------------------------------------+
    | 400    | Bad request       | Prints a warning; returns                     |
    |        |                   | ``(response.data, 400)``                      |
    +--------+-------------------+-----------------------------------------------+
    | 404    | Page not found    | Prints a warning; returns                     |
    |        |                   | ``(response.data, 404)``                      |
    +--------+-------------------+-----------------------------------------------+
    | Other  | Unexpected status | Prints the status code; returns               |
    |        |                   | ``(response.data, status)``                   |
    +--------+-------------------+-----------------------------------------------+

    :param pageNum: The page number to append to
                    ``https://www.thegradcafe.com/survey?page=`` when
                    constructing the request URL. Page numbering begins
                    at ``1``.
    :type pageNum: int
    :returns: A two-element tuple of ``(response.data, status)`` where
              ``response.data`` is the raw response body as bytes and
              ``status`` is the integer HTTP status code. Returned for
              all status codes, including error responses.
    :rtype: tuple[bytes, int]

    :raises urllib3.exceptions.MaxRetryError: If the HTTP connection
                                              fails after exhausting
                                              the retry policy
                                              configured on the
                                              module-level ``http``
                                              pool manager.
    :raises urllib3.exceptions.TimeoutError: If the request exceeds the
                                             timeout configured on
                                             ``http``.

    .. note::
        The delay is applied unconditionally before every request,
        including on the first call. If low-latency scraping is needed
        in a testing context, mock :func:`time.sleep` rather than
        removing the delay.

    .. warning::
        Non-200 status codes are handled by printing a message and
        falling through to ``return response.data, status`` rather than
        raising an exception. Callers must inspect the returned status
        code and handle error responses explicitly to avoid processing
        error page HTML as valid application data.

    .. warning::
        A ``500`` retry path is present in the source but commented out
        due to the risk of indefinite recursion if the server sustains
        a prolonged outage. If retry logic is reintroduced, use a
        capped retry counter or exponential backoff rather than
        unbounded recursion.
    """
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
    """
    Scrape and parse graduate application entries from GradCafe, stopping
    when previously fetched records are reached or pages are exhausted.

    Iterates through paginated GradCafe survey results page by page,
    fetching each via :func:`_fetchPage`, parsing the HTML table body
    with BeautifulSoup, and cleaning each page's rows via
    :func:`clean.clean_data`. Accumulates cleaned records across pages
    until one of the following termination conditions is met:

    **Termination conditions:**

    +------------------------------------------+---------------------------+
    | Condition                                | Behaviour                 |
    +==========================================+===========================+
    | HTTP status is not ``200``               | Returns ``None``          |
    +------------------------------------------+---------------------------+
    | :func:`clean.clean_data` returns ``None``| Stops pagination; returns |
    | (``lastIDFetched`` was encountered)      | accumulated data          |
    +------------------------------------------+---------------------------+
    | A page yields fewer than 20 records      | Stops pagination; returns |
    | (final or near-final page reached)       | accumulated data          |
    +------------------------------------------+---------------------------+
    | All pages exhausted without hitting      | Returns accumulated data  |
    | any other termination condition          |                           |
    +------------------------------------------+---------------------------+

    :param lastIDFetched: The integer ID of the most recently scraped
                          record from a prior run. Passed to
                          :func:`clean.clean_data` on each page to
                          detect where new data ends and already-seen
                          data begins. Pass ``0`` or ``None`` to scrape
                          all available records.
    :type lastIDFetched: int or None
    :returns: A flat list of cleaned application record dictionaries
              accumulated across all pages, or ``None`` if any page
              fetch returned a non-200 HTTP status. Returns an empty
              list if no new records were found before the last page.
    :rtype: list[dict] or None

    :raises AttributeError: If the parsed HTML page does not contain a
                            ``<tbody>`` element, causing
                            ``tableBody.find_all`` to be called on
                            ``None``.
    :raises Exception: Any unhandled exception raised by
                       :func:`_fetchPage` or :func:`clean.clean_data`,
                       such as network errors or malformed row
                       structure, will propagate to the caller uncaught.

    .. note::
        Each call to :func:`_fetchPage` incurs a random 0–5 second
        polite delay. For a dataset spanning ``n`` pages, expect a
        minimum wall-clock time of approximately ``n * 0`` seconds and
        a maximum of ``n * 5`` seconds, plus network latency.

    .. note::
        The ``< 20 records`` heuristic for detecting the final page
        assumes GradCafe serves exactly 20 entries per full page. If
        the source site changes its page size, this condition may
        terminate scraping prematurely or fail to detect the last page.

    .. warning::
        If ``tableBody`` is ``None`` (e.g. GradCafe changes its HTML
        structure or returns a CAPTCHA or error page with a ``200``
        status), ``tableBody.find_all("tr")`` will raise an
        :exc:`AttributeError` and scraping will abort without returning
        partial data. Consider adding a ``None`` guard on ``tableBody``
        before proceeding.

    .. seealso::
        :func:`_fetchPage` — fetches and returns raw page content for
        a given page number.

        :func:`clean.clean_data` — parses raw ``<tr>`` elements into
        cleaned record dictionaries and detects the ``lastIDFetched``
        boundary.
    """
    
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
    """
    Load and deserialise a JSON file from disk.

    Opens the file at ``fileName`` in read mode and parses its contents
    using :func:`json.load`, returning the deserialised Python object.
    The file is automatically closed when the ``with`` block exits,
    whether or not an exception occurs.

    :param fileName: Path to the JSON file to load. Accepts both
                     absolute and relative paths.
    :type fileName: str or os.PathLike
    :returns: The deserialised contents of the JSON file. The return
              type mirrors the top-level JSON structure — typically a
              :class:`dict` or :class:`list`.
    :rtype: dict or list

    :raises FileNotFoundError: If no file exists at ``fileName``.
    :raises PermissionError: If the process does not have read
                             permission for the file.
    :raises json.JSONDecodeError: If the file contents are not valid
                                  JSON.
    :raises IsADirectoryError: If ``fileName`` resolves to a directory
                               rather than a file.
    """
    with open(fileName, 'r') as f:
        return json.load(f)