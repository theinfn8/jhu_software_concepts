import json
import re
from bs4 import BeautifulSoup

baseURL = 'https://www.thegradcafe.com'

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

def _newRecord():
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

    >>> record = _newRecord()
    >>> record["university"]
    'None'
    >>> list(record.keys())[:3]
    ['id', 'program', 'university']
    """
    return dict.fromkeys(cols, "None")

def _processPrimaryRow(tr, tempDict):
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

    The following fields of ``tempDict`` are populated:

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
      ``baseURL`` and the anchor ``href``.
    - **id**: Integer record ID extracted from the anchor ``href``.

    :param tr: A BeautifulSoup ``<tr>`` tag representing a single
               application row from the primary results table.
    :type tr: bs4.element.Tag
    :param tempDict: A mutable record dictionary, typically initialised
                     by :func:`_newRecord`, which is updated in place.
    :type tempDict: dict
    :returns: None. ``tempDict`` is modified in place.
    :rtype: None

    :raises IndexError: If ``tr`` contains fewer than five ``<td>``
                        elements or the expected ``<span>`` tags are
                        missing from column 1.
    :raises ValueError: If the status cell does not contain the
                        delimiter ``" on "``.
    :raises KeyError: If the ``<a>`` tag in column 4 is missing or has
                      no ``href`` attribute.

    .. note::
        Depends on the module-level ``baseURL`` constant to construct
        the full record URL. The program name is normalized to title
        case via :func:`_titlecase`.
    """
    tableData = tr.find_all("td")
    # Row 1 field order = 0: University, 1: Degree Name and Type, 2: Date Added, 3: Status and Date of Status, 4: ID/URL
    
    # 0 University
    tempDict["university"] = str.strip(tableData[0].text)

    # 1 Degree Name and Type
    # Each element is in their own span tag
    spans = tableData[1].find_all("span")
    tempDict["program"] = _titlecase(str.strip(spans[0].text))
    tempDict["degree"] = str.strip(spans[1].text)

    # 2 Date added
    tempDict["date_added"] = str.strip(tableData[2].text)

    # 3 Statuses: Accepted, Rejected, Interview, Wait listed (Uniformity in the entry implies this is selected from a list)
    splitStatus = str.split(tableData[3].text, " on ")
    tempDict["status"] = str.strip(splitStatus[0])
    tempDict["status_date"] = str.strip(splitStatus[1])
    if tempDict["status"] == "Rejected":
        tempDict["rejected"] = tempDict["status_date"]
    elif tempDict["status"] == "Accepted":
        tempDict["accepted"] = tempDict["status_date"]

    # 4 ID and specific URL
    # Located in anchor tag, so grab the "a" and read the href
    anchor = tableData[4].find("a")
    tempDict["url"] = baseURL + anchor["href"]
    # We can pull out the ID so we have a unique identifier for later, so we might as well
    # And convert string ID to integer ID for easier reference later
    tempDict["id"] = int(str.split(anchor["href"], "/")[2])


def _processSecondaryRow(tr, tempDict):
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

    The following fields of ``tempDict`` are populated where present:

    - **term**: Enrollment term.
    - **US/International**: Applicant origin category.
    - **gpa**: Grade point average (optional).
    - **gre**: Composite GRE score (optional).
    - **grev**: GRE Verbal score (optional).
    - **greaw**: GRE Analytical Writing score (optional).

    :param tr: A BeautifulSoup ``<tr>`` tag representing a secondary
               row associated with a graduate application entry.
    :type tr: bs4.element.Tag
    :param tempDict: A mutable record dictionary, typically initialised
                     by :func:`_newRecord` and partially populated by
                     :func:`_processPrimaryRow`, which is updated in place.
    :type tempDict: dict
    :returns: None. ``tempDict`` is modified in place. Returns early if
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

def clean_data(tableRows, lastIDFetched):
    """
    Parse a list of raw HTML table rows into a list of clean application
    record dictionaries.

    Iterates over ``tableRows``, grouping every two or three consecutive
    rows into a single application record by delegating to
    :func:`_processPrimaryRow`, :func:`_processSecondaryRow`, and an
    inline comment extraction step. Stops early and returns accumulated
    data if the record matching ``lastIDFetched`` is encountered,
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

    If a record's ``id`` matches ``lastIDFetched``, parsing halts:

    - Returns ``None`` if no new records were collected before the match.
    - Returns the partially accumulated ``data`` list otherwise.

    :param tableRows: A list of BeautifulSoup ``<tr>`` tags comprising
                      the raw application results table, including
                      interleaved advertisement rows.
    :type tableRows: list[bs4.element.Tag]
    :param lastIDFetched: The integer ID of the most recently scraped
                          record from a prior run, used to avoid
                          reprocessing already-seen entries. Pass
                          ``None`` or ``0`` if no prior records exist.
    :type lastIDFetched: int or None
    :returns: A list of record dictionaries for new application entries,
              ``None`` if no new records were found before reaching
              ``lastIDFetched``, or the full list of parsed records if
              ``lastIDFetched`` is never encountered.
    :rtype: list[dict] or None

    :raises IndexError: If ``tableRows`` is malformed and a row group
                        boundary falls outside the list, e.g. if ad rows
                        are inserted at unexpected positions.
    :raises ValueError: If :func:`_processPrimaryRow` or
                        :func:`_processSecondaryRow` encounter
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

    >>> records = clean_data(tableRows, lastIDFetched=4812)
    >>> if records is None:
    ...     print("No new data found.")
    ... else:
    ...     print(f"{len(records)} new records fetched.")
    """
    data = list()

    i = 0
    entryCount = 0
    while i < len(tableRows):
        # Skip ad rows halfway through
        if entryCount == 10:
            i += 2

        tempDict = _newRecord()

        _processPrimaryRow(tableRows[i], tempDict)
        i += 1

        _processSecondaryRow(tableRows[i], tempDict)
        i += 1

        # Is there a third row with comments?
        p = tableRows[i].find("p")
        if p != None:
            tempDict["comments"] = p.text
            i += 1

        if tempDict['id'] == lastIDFetched:
            if len(data) == 0:
                return None
            else:
                return data
        
        if tempDict['id'] != 'None':
            data.append(tempDict)
        
        entryCount += 1
        
        # And skip the last ad row
        if entryCount == 20:
            i += 1
    
    return data