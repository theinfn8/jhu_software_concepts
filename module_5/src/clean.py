"""
GradCafe HTML row parsing and record cleaning utilities.

This module transforms raw BeautifulSoup ``<tr>`` table rows scraped
from GradCafe survey result pages into clean, structured application
record dictionaries. Each application entry on the source site spans
two or three consecutive table rows (a primary row, a secondary row,
and an optional comments row); this module groups those rows back
together, extracts and normalises their fields, skips interleaved
advertisement rows, and stops once previously-seen records are
reached.

This module is intended to be consumed by a scraping/orchestration
layer (such as a ``scrape`` module) that supplies raw ``<tr>`` tags and
receives back a list of plain dictionaries ready for storage or
serialisation.

**Module contents:**

+--------------------------------+--------------------------------------------+
| Name                            | Description                                 |
+==================================+============================================+
| :data:`BASE_URL`                | Root URL used to build absolute record URLs |
+--------------------------------+--------------------------------------------+
| :data:`cols`                    | Canonical schema/column order for records   |
+--------------------------------+--------------------------------------------+
| :func:`_titlecase`              | Title-case a string, preserving contractions |
+--------------------------------+--------------------------------------------+
| :func:`_new_record`             | Create an empty record from ``cols``         |
+--------------------------------+--------------------------------------------+
| :func:`_process_primary_row`    | Parse university/program/status/ID/URL row  |
+--------------------------------+--------------------------------------------+
| :func:`_process_secondary_row`  | Parse term/origin/GPA/GRE row                |
+--------------------------------+--------------------------------------------+
| :func:`clean_data`              | Public entry point: parse a full row list    |
+--------------------------------+--------------------------------------------+

**Dependencies:**

* :mod:`re` -- standard library, used by :func:`_titlecase` to locate
  and capitalise word tokens (including contractions).
* :mod:`bs4` (BeautifulSoup) -- expected but not imported directly in
  this module; all ``tr`` parameters are assumed to be
  :class:`bs4.element.Tag` instances supplied by the caller.

**Module-level constants:**

``BASE_URL``
    ``"https://www.thegradcafe.com"`` -- root URL prepended to relative
    ``href`` values extracted from primary rows to build each record's
    absolute ``url`` field. Must stay in sync with the equivalent
    constant used by the scraping/fetching layer.

``cols``
    The canonical, ordered list of field names defining the application
    record schema (``id``, ``program``, ``university``, ``comments``,
    ``date_added``, ``url``, ``status``, ``status_date``, ``accepted``,
    ``rejected``, ``term``, ``US/International``, ``degree``, ``gpa``,
    ``gre``, ``grev``, ``greaw``, ``llm-generated-program``,
    ``llm-generated-university``). Used by :func:`_new_record` to
    initialise every record with a consistent set of keys, each
    defaulted to the string ``"None"``.

.. warning::
    Unset fields default to the **string** ``"None"`` rather than the
    Python singleton :data:`None`. Downstream code that checks
    ``value is None`` to detect missing data will not work as
    expected; checks must compare against the string ``"None"``
    instead.

.. warning::
    :func:`clean_data` contains hardcoded advertisement-skipping logic
    (2 rows skipped after the 10th entry, 1 row skipped after the
    20th). This assumes a fixed, unchanging ad layout on the source
    site; if GradCafe alters ad placement or frequency, row alignment
    will break and parsing will likely raise :exc:`IndexError` or
    silently produce corrupted records.

.. note::
    The two ``llm-generated-*`` columns in ``cols`` (program and
    university name normalisation) are part of the record schema but
    are not populated by any function in this module; they are
    presumably filled in by a separate, later processing step not
    contained here.

.. note::
    Functions prefixed with an underscore (:func:`_titlecase`,
    :func:`_new_record`, :func:`_process_primary_row`,
    :func:`_process_secondary_row`) are internal helpers.
    :func:`clean_data` is the only function intended for use by
    external callers.

**Typical usage:**

.. code-block:: python

    from bs4 import BeautifulSoup
    from src import clean

    soup = BeautifulSoup(page_html, "html.parser")
    table_rows = soup.find("tbody").find_all("tr")

    records = clean.clean_data(table_rows, last_id_fetched=4812)
    if records is None:
        print("No new data found.")
    else:
        print(f"{len(records)} new records parsed.")

.. seealso::
    The scraping/orchestration module that supplies ``table_rows`` to
    :func:`clean_data` and consumes its returned records (e.g. for
    persistence or further LLM-based normalisation of
    ``llm-generated-program`` / ``llm-generated-university``).
"""
import re

BASE_URL = 'https://www.thegradcafe.com'

def _titlecase(s):
    """
    Convert a string to title case, preserving contractions.

    Uses a regular expression to capitalize the first letter of each word
    while correctly handling contractions (e.g. ``don't`` → ``Don't``).

    :param s: The input string to convert to title case.
    :type s: str
    :returns: The input string with each word capitalized.
    :rtype: str

    :Example:

    >>> _titlecase("the quick brown fox")
    'The Quick Brown Fox'
    >>> _titlecase("don't stop me now")
    "Don't Stop Me Now"
    """
    return re.sub(r"[A-Za-z]+('[A-Za-z]+)?",
                  lambda word: word.group(0).capitalize(),
                  s)

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
        "llm-generated-program",
        "llm-generated-university"
]

def _new_record():
    """
    Create a new empty record with all application fields set to ``"None"``.

    Generates a dictionary keyed by the module-level ``cols`` list, which
    defines the full schema for a graduate program application entry.
    Every field is initialized to the string ``"None"``.

    The resulting record contains the following fields:

    - **id**: Unique identifier for the record.
    - **program**: Name of the graduate program applied to.
    - **university**: Name of the university.
    - **comments**: Applicant or community comments on the application.
    - **date_added**: Date the record was added.
    - **url**: Source URL for the application result.
    - **status**: Current application status.
    - **status_date**: Date of the most recent status update.
    - **accepted**: Whether the applicant was accepted.
    - **rejected**: Whether the applicant was rejected.
    - **term**: Enrollment term (e.g. Fall 2025).
    - **US/International**: Whether the applicant is a US or international student.
    - **degree**: Degree type being pursued (e.g. MS, PhD).
    - **gpa**: Applicant's GPA.
    - **gre**: GRE total score.
    - **grev**: GRE Verbal score.
    - **greaw**: GRE Analytical Writing score.
    - **llm-generated-program**: LLM-normalized program name.
    - **llm-generated-university**: LLM-normalized university name.

    :returns: A dictionary mapping each column name in ``cols`` to the
              string ``"None"``.
    :rtype: dict

    :Example:

    >>> record = _new_record()
    >>> record["university"]
    'None'
    >>> list(record.keys())[:3]
    ['id', 'program', 'university']
    """
    return dict.fromkeys(cols, "None")

def _process_primary_row(tr, temp_dict):
    """
    Parse a primary table row and populate the record dictionary with
    application data.

    Extracts and cleans fields from an HTML ``<tr>`` element representing
    a graduate application entry. The row is expected to contain exactly
    five ``<td>`` columns in the following order:

    +-------+----------------------------------+-------------------------------+
    | Index | Column                           | Notes                         |
    +=======+==================================+===============================+
    | 0     | University                       | Plain text                    |
    +-------+----------------------------------+-------------------------------+
    | 1     | Program name and degree type     | Each in a separate ``<span>`` |
    +-------+----------------------------------+-------------------------------+
    | 2     | Date added                       | Plain text                    |
    +-------+----------------------------------+-------------------------------+
    | 3     | Status and status date           | Separated by ``" on "``       |
    +-------+----------------------------------+-------------------------------+
    | 4     | Record ID and URL                | Extracted from ``<a href>``   |
    +-------+----------------------------------+-------------------------------+

    The following fields of ``temp_dict`` are populated:

    - **university**: Stripped university name.
    - **program**: Title-cased program name from the first ``<span>``.
    - **degree**: Degree type from the second ``<span>``.
    - **date_added**: Date the record was added.
    - **status**: Application status (e.g. ``Accepted``, ``Rejected``,
      ``Interview``, ``Wait Listed``).
    - **status_date**: Date of the status update.
    - **accepted**: Set to ``status_date`` if status is ``Accepted``,
      otherwise remains ``"None"``.
    - **rejected**: Set to ``status_date`` if status is ``Rejected``,
      otherwise remains ``"None"``.
    - **url**: Full URL to the application entry, constructed from
      ``BASE_URL`` and the anchor ``href``.
    - **id**: Integer record ID extracted from the anchor ``href``.

    :param tr: A BeautifulSoup ``<tr>`` tag representing a single
               application row from the primary results table.
    :type tr: bs4.element.Tag
    :param temp_dict: A mutable record dictionary, typically initialised
                     by :func:`_newRecord`, which is updated in place.
    :type temp_dict: dict
    :returns: None. ``temp_dict`` is modified in place.
    :rtype: None

    :raises IndexError: If ``tr`` contains fewer than five ``<td>``
                        elements or the expected ``<span>`` tags are
                        missing from column 1.
    :raises ValueError: If the status cell does not contain the
                        delimiter ``" on "``.
    :raises KeyError: If the ``<a>`` tag in column 4 is missing or has
                      no ``href`` attribute.

    .. note::
        Depends on the module-level ``BASE_URL`` constant to construct
        the full record URL. The program name is normalized to title
        case via :func:`_titlecase`.
    """
    table_data = tr.find_all("td")
    # Row 1 field order = 0: University, 1: Degree Name and Type, 2: Date Added,
    # 3: Status and Date of Status, 4: ID/URL

    # 0 University
    temp_dict["university"] = str.strip(table_data[0].text)

    # 1 Degree Name and Type
    # Each element is in their own span tag
    spans = table_data[1].find_all("span")
    temp_dict["program"] = _titlecase(str.strip(spans[0].text))
    temp_dict["degree"] = str.strip(spans[1].text)

    # 2 Date added
    temp_dict["date_added"] = str.strip(table_data[2].text)

    # 3 Statuses: Accepted, Rejected, Interview, Wait listed (Uniformity in
    # the entry implies this is selected from a list)
    split_status = str.split(table_data[3].text, " on ")
    temp_dict["status"] = str.strip(split_status[0])
    temp_dict["status_date"] = str.strip(split_status[1])
    if temp_dict["status"] == "Rejected":
        temp_dict["rejected"] = temp_dict["status_date"]
    elif temp_dict["status"] == "Accepted":
        temp_dict["accepted"] = temp_dict["status_date"]

    # 4 ID and specific URL
    # Located in anchor tag, so grab the "a" and read the href
    anchor = table_data[4].find("a")
    temp_dict["url"] = BASE_URL + anchor["href"]
    # We can pull out the ID so we have a unique identifier for later, so we might as well
    # And convert string ID to integer ID for easier reference later
    temp_dict["id"] = int(str.split(anchor["href"], "/")[2])


def _process_secondary_row(tr, temp_dict):
    """
    Parse a secondary table row and populate the record dictionary with
    supplemental applicant data.

    Extracts term, applicant origin, and optional test score fields from
    the ``<div>`` elements within a secondary ``<tr>`` row. The first two
    ``<div>`` elements are skipped as they contain layout and duplicate
    status information respectively.

    The expected ``<div>`` structure is:

    +-------+---------------------------+-------------------------------+
    | Index | Content                   | Notes                         |
    +=======+===========================+===============================+
    | 0     | Flex grid container       | Layout only — skipped         |
    +-------+---------------------------+-------------------------------+
    | 1     | Repeated status info      | Hidden element — skipped      |
    +-------+---------------------------+-------------------------------+
    | 2     | Enrollment term           | e.g. ``Fall 2025``            |
    +-------+---------------------------+-------------------------------+
    | 3     | US or International       | e.g. ``U.S.``                 |
    +-------+---------------------------+-------------------------------+
    | 4+    | Optional test score boxes | GPA, GRE, GRE V, GRE AW      |
    +-------+---------------------------+-------------------------------+

    Each optional score box (index 4 and beyond) is parsed by token count:

    - **2 tokens** — ``GPA <value>`` or ``GRE <value>``
    - **3 tokens** — ``GRE V <value>`` or ``GRE AW <value>``

    The following fields of ``temp_dict`` are populated where present:

    - **term**: Enrollment term.
    - **US/International**: Applicant origin category.
    - **gpa**: Grade point average (optional).
    - **gre**: Composite GRE score (optional).
    - **grev**: GRE Verbal score (optional).
    - **greaw**: GRE Analytical Writing score (optional).

    :param tr: A BeautifulSoup ``<tr>`` tag representing a secondary
               row associated with a graduate application entry.
    :type tr: bs4.element.Tag
    :param temp_dict: A mutable record dictionary, typically initialised
                     by :func:`_newRecord` and partially populated by
                     :func:`_processPrimaryRow`, which is updated in place.
    :type temp_dict: dict
    :returns: None. ``temp_dict`` is modified in place. Returns early if
              no optional score boxes are present (i.e. fewer than 5
              ``<div>`` elements).
    :rtype: None

    :raises IndexError: If ``tr`` contains fewer than four ``<div>``
                        elements, meaning the expected term or
                        US/International fields are missing.

    .. note::
        Score fields that are absent from the row are left at their
        initialised value of ``"None"`` and are silently skipped.
        Unrecognised token patterns in optional boxes are also silently
        ignored.
    """
    divs = tr.find_all("div")
    # 0 div sets up the flex grid for the row ** Skip it
    # 1 div repeats status info, but is hidden ** Skip it

    # 2 Term
    temp_dict["term"] = divs[2].text

    # 3 US or International
    temp_dict["US/International"] = divs[3].text

    # If there are no other flex boxes, exit
    if len(divs) == 4:
        return

    # Else the complicated parse
    for i in range(4, len(divs)):
        parsed_box = str.split(divs[i].text)

        # If we have two items it should be GPA or GRE
        if len(parsed_box) == 2:
            if parsed_box[0] == 'GPA':
                # Got a GPA
                temp_dict["gpa"] = parsed_box[1]
            elif parsed_box[0] == 'GRE':
                # Got the regular GRE
                temp_dict["gre"] = parsed_box[1]

        # If we have three items, it's one of the other GREs
        elif len(parsed_box) == 3:
            if parsed_box[1] == 'V':
                temp_dict["grev"] = parsed_box[2]
            if parsed_box[1] == 'AW':
                temp_dict["greaw"] = parsed_box[2]

def clean_data(table_rows, last_id_fetched):
    """
    Parse a list of raw HTML table rows into a list of clean application
    record dictionaries.

    Iterates over ``table_rows``, grouping every two or three consecutive
    rows into a single application record by delegating to
    :func:`_processPrimaryRow`, :func:`_process_secondary_row`, and an
    inline comment extraction step. Stops early and returns accumulated
    data if the record matching ``last_id_fetched`` is encountered,
    indicating that previously scraped content has been reached.

    **Row grouping structure:**

    Each application entry occupies two or three consecutive rows:

    +--------+------------------+------------------------------------------+
    | Offset | Row type         | Notes                                    |
    +========+==================+==========================================+
    | +0     | Primary row      | University, program, status, ID, URL     |
    +--------+------------------+------------------------------------------+
    | +1     | Secondary row    | Term, origin, GPA, GRE scores            |
    +--------+------------------+------------------------------------------+
    | +2     | Comments row     | Optional; present only if a ``<p>`` tag  |
    |        | (optional)       | is found                                 |
    +--------+------------------+------------------------------------------+

    **Advertisement row skipping:**

    The source table intersperses advertisement rows at fixed positions:

    - 2 ad rows are skipped after every 10th entry (before entry 11).
    - 1 ad row is skipped after the 20th entry.

    **Early termination:**

    If a record's ``id`` matches ``last_id_fetched``, parsing halts:

    - Returns ``None`` if no new records were collected before the match.
    - Returns the partially accumulated ``data`` list otherwise.

    :param table_rows: A list of BeautifulSoup ``<tr>`` tags comprising
                      the raw application results table, including
                      interleaved advertisement rows.
    :type table_rows: list[bs4.element.Tag]
    :param last_id_fetched: The integer ID of the most recently scraped
                          record from a prior run, used to avoid
                          reprocessing already-seen entries. Pass
                          ``None`` or ``0`` if no prior records exist.
    :type last_id_fetched: int or None
    :returns: A list of record dictionaries for new application entries,
              ``None`` if no new records were found before reaching
              ``last_id_fetched``, or the full list of parsed records if
              ``last_id_fetched`` is never encountered.
    :rtype: list[dict] or None

    :raises IndexError: If ``table_rows`` is malformed and a row group
                        boundary falls outside the list, e.g. if ad rows
                        are inserted at unexpected positions.
    :raises ValueError: If :func:`_processPrimaryRow` or
                        :func:`_process_secondary_row` encounter
                        unexpected cell structure within a row.

    .. note::
        Records with an ``id`` of ``"None"`` (i.e. where ID extraction
        failed) are silently discarded and not appended to ``data``.

    .. warning::
        The ad-skipping logic is hardcoded to positions after entries 10
        and 20, reflecting the current structure of the source table.
        Changes to the ad placement on the source site will cause row
        misalignment and likely raise an :exc:`IndexError`.

    :Example:

    >>> records = clean_data(table_rows, last_id_fetched=4812)
    >>> if records is None:
    ...     print("No new data found.")
    ... else:
    ...     print(f"{len(records)} new records fetched.")
    """
    data = []

    i = 0
    entry_count = 0
    while i < len(table_rows):
        # Skip ad rows halfway through
        if entry_count == 10:
            i += 2

        temp_dict = _new_record()

        _process_primary_row(table_rows[i], temp_dict)
        i += 1

        _process_secondary_row(table_rows[i], temp_dict)
        i += 1

        # Is there a third row with comments?
        p = table_rows[i].find("p")
        if p is not None:
            temp_dict["comments"] = p.text
            i += 1

        if temp_dict['id'] == last_id_fetched:
            if len(data) == 0:
                return None

            return data

        if temp_dict['id'] != 'None':
            data.append(temp_dict)

        entry_count += 1

        # And skip the last ad row
        if entry_count == 20:
            i += 1

    return data
