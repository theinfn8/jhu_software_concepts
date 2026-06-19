"""
GradCafe survey scraper and JSON loader.

This module provides utilities for scraping graduate school admission
result entries from `TheGradCafe <https://www.thegradcafe.com>` survey
pages, and for loading previously persisted JSON datasets from disk.

It paginates through GradCafe's public survey listing, fetches each
page's raw HTML via :mod:`urllib3`, parses the results table with
:mod:`bs4` (BeautifulSoup), and delegates row-level parsing and
deduplication logic to :func:`src.clean.clean_data`. Scraping stops once
previously seen records are reached (tracked via a ``last_id_fetched``
marker) or once the underlying source is exhausted.

**Module contents:**

+---------------------------+------------------------------------------+
| Name                      | Description                               |
+===========================+============================================+
| :func:`_fetch_page`       | Fetch a single paginated page of results  |
+---------------------------+------------------------------------------+
| :func:`scrape_data`       | Orchestrate pagination, parsing, cleaning |
+---------------------------+------------------------------------------+
| :func:`load_data`         | Load a JSON file from disk                |
+---------------------------+------------------------------------------+

**Dependencies:**

* :mod:`json` -- standard library, used by :func:`load_data`.
* :mod:`time` -- standard library, used to throttle requests.
* :mod:`random` -- standard library, used to randomise request delays.
* :mod:`urllib3` -- third-party, supplies the :class:`~urllib3.PoolManager`
  used for HTTP requests.
* :mod:`bs4` (BeautifulSoup) -- third-party, used to parse HTML survey
  tables.
* :mod:`src.clean` -- local package, supplies
  :func:`~src.clean.clean_data` for row-level cleaning and
  deduplication.

**Module-level constants:**

``BASE_PAGE_URL``
    Base URL stem (``"https://www.thegradcafe.com/survey?page="``) onto
    which a page number is appended by :func:`_fetch_page`.

``BASE_PAGE_URL_SORT_ORDER``
    Query-string suffix (``"&sort=newest"``) appended after the page
    number to request results in newest-first order.

``BASE_URL``
    The root site URL (``"https://www.thegradcafe.com"``). Not directly
    referenced within this module, but exposed for callers that need to
    resolve relative links found in scraped HTML.

``SOURCE_COLS``
    ``["page", "html"]`` -- intended column labels for caching raw
    scraped page content alongside its page number; not directly used
    elsewhere in this module.

``http``
    A module-level, shared :class:`urllib3.PoolManager` instance used
    for all outbound HTTP requests, instantiated once at import time.

.. warning::
    ``http`` is a shared, mutable, module-level instance. Tests that
    monkeypatch or reset connection pools should do so carefully, since
    state is shared across all callers of this module.

**Typical usage:**

.. code-block:: python

    from src import scrape

    # Scrape everything newer than a previously stored record id
    records = scrape.scrape_data(last_id_fetched=123456)

    if records is not None:
        print(f"Scraped {len(records)} new records")

    # Load a previously saved dataset
    existing = scrape.load_data("data/applicant_data.json")

.. note::
    Network access is required for :func:`scrape_data` and
    :func:`_fetch_page`; :func:`load_data` operates purely on local
    files and has no network dependency.

.. seealso::
    :mod:`src.clean` for the row-parsing and deduplication logic
    invoked during scraping.
"""

import json
import time
import random

from urllib3 import PoolManager
from bs4 import BeautifulSoup

from src import clean

BASE_PAGE_URL = 'https://www.thegradcafe.com/survey?page='
BASE_PAGE_URL_SORT_ORDER = '&sort=newest'
BASE_URL = 'https://www.thegradcafe.com'
http = PoolManager()

SOURCE_COLS = [
        "page",
        "html"
    ]

def _fetch_page(page_num):
    """
    Fetch a single paginated results page from GradCafe with a polite
    random delay.

    Constructs the target URL by interpolating ``page_num`` between the
    module-level ``BASE_PAGE_URL`` and ``BASE_PAGE_URL_SORT_ORDER`` constants,
    issues an HTTP GET request via the module-level ``http`` pool
    manager, and returns the raw response body and status code.

    A random delay of 0–5 seconds is applied before each request to
    avoid overwhelming the source server.

    **URL construction:**

    .. code-block:: text

        https://www.thegradcafe.com/survey?page={page_num}&sort=newest

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

    :param page_num: The page number to append to
                    ``https://www.thegradcafe.com/survey?page=`` when
                    constructing the request URL. Page numbering begins
                    at ``1``.
    :type page_num: int
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

    url = BASE_PAGE_URL + str(page_num) + BASE_PAGE_URL_SORT_ORDER
    response = http.request('GET', url)
    status = response.status

    if status == 200:
        return response.data, status
    # Could cause an indefinite loop if the server is having major issues, rethink this and fix it
    # elif status == 500:
    #     # Internal server error, lets wait a little bit and retry
    #     time.sleep(5)
    #     return _fetch_page(page_num)

    if status == 400:
        # Bad request, exit
        print("Bad Request on Base Page")

    elif status == 404:
        # Exit if no page found
        print("Base Page not found")

    else:
        print(f"An unexpected HTTP result was returned: {status}")

    return response.data, status


def scrape_data(last_id_fetched):
    """
    Scrape and parse graduate application entries from GradCafe, stopping
    when previously fetched records are reached or pages are exhausted.

    Iterates through paginated GradCafe survey results page by page,
    fetching each via :func:`_fetch_page`, parsing the HTML table body
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
    | (``last_id_fetched`` was encountered)      | accumulated data          |
    +------------------------------------------+---------------------------+
    | A page yields fewer than 20 records      | Stops pagination; returns |
    | (final or near-final page reached)       | accumulated data          |
    +------------------------------------------+---------------------------+
    | All pages exhausted without hitting      | Returns accumulated data  |
    | any other termination condition          |                           |
    +------------------------------------------+---------------------------+

    :param last_id_fetched: The integer ID of the most recently scraped
                          record from a prior run. Passed to
                          :func:`clean.clean_data` on each page to
                          detect where new data ends and already-seen
                          data begins. Pass ``0`` or ``None`` to scrape
                          all available records.
    :type last_id_fetched: int or None
    :returns: A flat list of cleaned application record dictionaries
              accumulated across all pages, or ``None`` if any page
              fetch returned a non-200 HTTP status. Returns an empty
              list if no new records were found before the last page.
    :rtype: list[dict] or None

    :raises AttributeError: If the parsed HTML page does not contain a
                            ``<tbody>`` element, causing
                            ``table_body.find_all`` to be called on
                            ``None``.
    :raises Exception: Any unhandled exception raised by
                       :func:`_fetch_page` or :func:`clean.clean_data`,
                       such as network errors or malformed row
                       structure, will propagate to the caller uncaught.

    .. note::
        Each call to :func:`_fetch_page` incurs a random 0–5 second
        polite delay. For a dataset spanning ``n`` pages, expect a
        minimum wall-clock time of approximately ``n * 0`` seconds and
        a maximum of ``n * 5`` seconds, plus network latency.

    .. note::
        The ``< 20 records`` heuristic for detecting the final page
        assumes GradCafe serves exactly 20 entries per full page. If
        the source site changes its page size, this condition may
        terminate scraping prematurely or fail to detect the last page.

    .. warning::
        If ``table_body`` is ``None`` (e.g. GradCafe changes its HTML
        structure or returns a CAPTCHA or error page with a ``200``
        status), ``table_body.find_all("tr")`` will raise an
        :exc:`AttributeError` and scraping will abort without returning
        partial data. Consider adding a ``None`` guard on ``table_body``
        before proceeding.

    .. seealso::
        :func:`_fetch_page` — fetches and returns raw page content for
        a given page number.

        :func:`clean.clean_data` — parses raw ``<tr>`` elements into
        cleaned record dictionaries and detects the ``last_id_fetched``
        boundary.
    """

    current_page = 1

    clean_data = []

    fetch_more_entries = True

    while fetch_more_entries:
        content, status = _fetch_page(current_page)

        if status != 200:
            return None

        parsed_page = BeautifulSoup(content, "html.parser")

        table_body = parsed_page.find("tbody")
        table_rows = table_body.find_all("tr")

        new_cleaned_data = clean.clean_data(table_rows, last_id_fetched)
        if new_cleaned_data is None:
            fetch_more_entries = False
        else:
            if len(new_cleaned_data) < 20:
                fetch_more_entries = False
            clean_data = clean_data + new_cleaned_data

        current_page += 1

    return clean_data

def load_data(file_name):
    """
    Load and deserialise a JSON file from disk.

    Opens the file at ``file_name`` in read mode and parses its contents
    using :func:`json.load`, returning the deserialised Python object.
    The file is automatically closed when the ``with`` block exits,
    whether or not an exception occurs.

    :param file_name: Path to the JSON file to load. Accepts both
                     absolute and relative paths.
    :type file_name: str or os.PathLike
    :returns: The deserialised contents of the JSON file. The return
              type mirrors the top-level JSON structure — typically a
              :class:`dict` or :class:`list`.
    :rtype: dict or list

    :raises FileNotFoundError: If no file exists at ``file_name``.
    :raises PermissionError: If the process does not have read
                             permission for the file.
    :raises json.JSONDecodeError: If the file contents are not valid
                                  JSON.
    :raises IsADirectoryError: If ``file_name`` resolves to a directory
                               rather than a file.
    """
    with open(file_name, 'r', encoding="utf-8") as f:
        return json.load(f)
