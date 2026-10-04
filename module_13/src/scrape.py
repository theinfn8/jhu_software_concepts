"""
GradCafe survey scraper and JSON loader.

This module provides utilities for scraping graduate school admission
result entries from `TheGradCafe <https://www.thegradcafe.com>` survey
pages, and for loading previously persisted JSON datasets from disk.

GradCafe paginates results with an opaque ``?cursor=...`` token rather
than a page number: each page's HTML includes a "Next" link whose
``href`` carries the cursor for the following page. This module
follows that chain of links directly (see :func:`_extract_next_url`)
rather than constructing URLs from a counter, since page numbers are
no longer a valid way to request a given page of results.

It fetches each page's raw HTML via :mod:`urllib3`, parses the results
table with :mod:`bs4` (BeautifulSoup), and delegates row-level parsing
and deduplication logic to :func:`src.clean.clean_data`. Scraping stops
once previously seen records are reached (tracked via a
``last_id_fetched`` marker) or once no further "Next" link is found.

**Module contents:**

+---------------------------+------------------------------------------+
| Name                      | Description                               |
+===========================+============================================+
| :func:`_fetch_page`       | Fetch a single results page by full URL   |
+---------------------------+------------------------------------------+
| :func:`_extract_next_url` | Find the "Next" link's absolute URL       |
+---------------------------+------------------------------------------+
| :func:`scrape_data`       | Orchestrate pagination, parsing, cleaning |
+---------------------------+------------------------------------------+
| :func:`load_data`         | Load a JSON file from disk                |
+---------------------------+------------------------------------------+

**Dependencies:**

* :mod:`json` -- standard library, used by :func:`load_data`.
* :mod:`time` -- standard library, used to throttle requests.
* :mod:`random` -- standard library, used to randomise request delays.
* :mod:`urllib.parse` -- standard library, used to resolve the
  "Next" link's ``href`` into an absolute URL.
* :mod:`urllib3` -- third-party, supplies the
  :class:`~urllib3.PoolManager` used for HTTP requests.
* :mod:`bs4` (BeautifulSoup) -- third-party, used to parse HTML survey
  tables.
* :mod:`src.clean` -- local package, supplies
  :func:`~src.clean.clean_data` for row-level cleaning and
  deduplication.

**Module-level constants:**

``BASE_URL``
    The root site URL (``"https://www.thegradcafe.com"``), used both
    to build the initial request and to resolve relative "Next" links
    into absolute URLs.

``INITIAL_URL``
    The first page requested (``sort=newest``). Every subsequent page
    is reached by following the "Next" link discovered on the
    previous page, which already reflects this same sort context.

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
from urllib.parse import urljoin

from urllib3 import PoolManager
from bs4 import BeautifulSoup

from src import clean

BASE_URL = 'https://www.thegradcafe.com'
SURVEY_URL = f'{BASE_URL}/survey'

# The sort order only needs to be requested on the *first* page. Every
# subsequent page is reached by following the site's own "Next" link
# (which carries an opaque ?cursor=... token), and that link already
# reflects whatever sort/filter context produced the current page.
INITIAL_URL = f'{SURVEY_URL}?sort=newest'

http = PoolManager()


def _fetch_page(url):
    """
    Fetch a single survey results page by its full URL, with a polite
    random delay.

    Unlike the old ``?page=N`` scheme, GradCafe now paginates with an
    opaque ``?cursor=...`` token that must be read off the "Next" link
    on the previously fetched page -- pages can no longer be requested
    by number, only by following the chain of cursor links forward.

    A random delay of 0-5 seconds is applied before each request to
    avoid overwhelming the source server.

    :param url: The full URL to fetch -- either :data:`INITIAL_URL` or
        a cursor URL discovered from the previous page's "Next" link.
    :type url: str
    :returns: A two-element tuple of ``(response.data, status)`` where
        ``response.data`` is the raw response body as bytes and
        ``status`` is the integer HTTP status code. Returned for all
        status codes, including error responses.
    :rtype: tuple[bytes, int]

    :raises urllib3.exceptions.MaxRetryError: If the HTTP connection
        fails after exhausting the retry policy configured on the
        module-level ``http`` pool manager.
    :raises urllib3.exceptions.TimeoutError: If the request exceeds
        the timeout configured on ``http``.

    .. note::
        The delay is applied unconditionally before every request,
        including on the first call. If low-latency scraping is
        needed in a testing context, mock :func:`time.sleep` rather
        than removing the delay.

    .. warning::
        Non-200 status codes are handled by printing a message and
        falling through to ``return response.data, status`` rather
        than raising an exception. Callers must inspect the returned
        status code and handle error responses explicitly to avoid
        processing error page HTML as valid application data.
    """
    # Build in wait time for politeness
    time.sleep(random.randint(0, 5))

    response = http.request('GET', url)
    status = response.status

    if status == 200:
        return response.data, status

    if status == 400:
        # Bad request, exit
        print("Bad Request on Survey Page")

    elif status == 404:
        # Exit if no page found
        print("Survey Page not found")

    else:
        print(f"An unexpected HTTP result was returned: {status}")

    return response.data, status


def _extract_next_url(parsed_page):
    """
    Find the absolute URL of the "Next" pagination link on a page.

    Tries a few strategies since GradCafe's exact markup for the
    pagination control isn't something we control or can guarantee
    stays identical across front-end changes:

      1. An ``<a>`` tag with ``rel="next"``.
      2. An ``<a>`` tag whose visible text is exactly "Next"
         (case-insensitive) -- matches what's currently rendered.
      3. Fallback: any ``<a>`` tag whose ``href`` contains a
         ``cursor=`` query parameter.

    :param parsed_page: A BeautifulSoup-parsed survey results page.
    :returns: The absolute next-page URL, or ``None`` if no "Next"
        link was found (i.e. we've reached the last page of results).
    :rtype: str or None
    """
    next_link = parsed_page.find("a", rel="next")

    if next_link is None:
        for a in parsed_page.find_all("a", href=True):
            if a.get_text(strip=True).lower() == "next":
                next_link = a
                break

    if next_link is None:
        for a in parsed_page.find_all("a", href=True):
            if "cursor=" in a["href"]:
                next_link = a
                break

    if next_link is None:
        return None

    return urljoin(BASE_URL, next_link["href"])


def scrape_data(last_id_fetched):
    """
    Scrape and parse graduate application entries from GradCafe,
    stopping when previously fetched records are reached or no further
    pages remain.

    Starts from :data:`INITIAL_URL` and follows each page's "Next"
    link (see :func:`_extract_next_url`), fetching via
    :func:`_fetch_page`, parsing the HTML table body with
    BeautifulSoup, and cleaning each page's rows via
    :func:`clean.clean_data`. Accumulates cleaned records across pages
    until one of the following termination conditions is met:

    **Termination conditions:**

    +-------------------------------------------+---------------------------+
    | Condition                                  | Behaviour                 |
    +=============================================+===========================+
    | HTTP status is not ``200``                 | Returns ``None``          |
    +-------------------------------------------+---------------------------+
    | :func:`clean.clean_data` returns ``None``  | Stops pagination; returns |
    | (``last_id_fetched`` was encountered)      | accumulated data          |
    +-------------------------------------------+---------------------------+
    | No further "Next" link found on a page     | Stops pagination; returns |
    | (end of results)                           | accumulated data          |
    +-------------------------------------------+---------------------------+

    :param last_id_fetched: The integer ID of the most recently
        scraped record from a prior run. Passed to
        :func:`clean.clean_data` on each page to detect where new data
        ends and already-seen data begins. Pass ``0`` or ``None`` to
        scrape all available records.
    :type last_id_fetched: int or None
    :returns: A flat list of cleaned application record dictionaries
        accumulated across all pages, or ``None`` if any page fetch
        returned a non-200 HTTP status.
    :rtype: list[dict] or None

    :raises AttributeError: If a parsed HTML page does not contain a
        ``<tbody>`` element, causing ``table_body.find_all`` to be
        called on ``None``.
    :raises Exception: Any unhandled exception raised by
        :func:`_fetch_page` or :func:`clean.clean_data` propagates to
        the caller uncaught.

    .. seealso::
        :func:`_fetch_page` -- fetches and returns raw page content
        for a given URL.

        :func:`_extract_next_url` -- finds the next page's URL from
        the current page's "Next" link.

        :func:`clean.clean_data` -- parses raw ``<tr>`` elements into
        cleaned record dictionaries and detects the
        ``last_id_fetched`` boundary.
    """
    current_url = INITIAL_URL

    cleaned_data = []

    fetch_more_entries = True

    print(f"Scrape initiated. Stopping on entry {last_id_fetched}")

    while fetch_more_entries:
        content, status = _fetch_page(current_url)

        if status != 200:
            return None

        parsed_page = BeautifulSoup(content, "html.parser")

        table_body = parsed_page.find("tbody")
        table_rows = table_body.find_all("tr")

        new_cleaned_data = clean.clean_data(table_rows, last_id_fetched)
        if new_cleaned_data is None:
            fetch_more_entries = False
        else:
            cleaned_data = cleaned_data + new_cleaned_data

            next_url = _extract_next_url(parsed_page)
            if next_url is None:
                # No "Next" link -- we've reached the end of the results.
                fetch_more_entries = False
            else:
                current_url = next_url

    return cleaned_data


def load_data(file_name):
    """
    Load and deserialise a JSON file from disk.

    Opens the file at ``file_name`` in read mode and parses its
    contents using :func:`json.load`, returning the deserialised
    Python object. The file is automatically closed when the ``with``
    block exits, whether or not an exception occurs.

    :param file_name: Path to the JSON file to load. Accepts both
        absolute and relative paths.
    :type file_name: str or os.PathLike
    :returns: The deserialised contents of the JSON file. The return
        type mirrors the top-level JSON structure -- typically a
        :class:`dict` or :class:`list`.
    :rtype: dict or list

    :raises FileNotFoundError: If no file exists at ``file_name``.
    :raises PermissionError: If the process does not have read
        permission for the file.
    :raises json.JSONDecodeError: If the file contents are not valid
        JSON.
    :raises IsADirectoryError: If ``file_name`` resolves to a
        directory rather than a file.
    """
    with open(file_name, 'r', encoding="utf-8") as f:
        return json.load(f)
