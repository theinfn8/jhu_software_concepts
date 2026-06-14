from flask import Blueprint, render_template
import psycopg
from src import query_data
from src import scrape
from src import load_data
from src.config import config

updating = False

bp = Blueprint('core', __name__, template_folder="templates", static_folder="static", static_url_path='/core/static')

def getAnalysisHTML():
    """
    Query the database for all eleven analytical statistics and render
    them as an HTML unordered list string.

    Opens a single database connection using the module-level ``config``
    dictionary, collects answers to all eleven questions by delegating
    to the corresponding functions in the ``query_data`` module, then
    interpolates the results into a formatted HTML ``<ul>`` fragment.
    The connection is automatically closed when the ``with`` block exits.

    This function is the web-facing equivalent of :func:`getStats` —
    it executes the same eleven queries but returns an HTML string
    suitable for embedding in a Flask template rather than printing
    to stdout.

    **Queries and HTML mapping:**

    +-----+---------------------------------------+------------------------------------------+
    | No. | Question summary                      | Delegated to                             |
    +=====+=======================================+==========================================+
    | 1   | Fall 2026 entry count                 | :func:`query_data.getTermCount`          |
    +-----+---------------------------------------+------------------------------------------+
    | 2   | International applicant percentage    | :func:`query_data.getInternationalAverage`|
    +-----+---------------------------------------+------------------------------------------+
    | 3   | Average GPA, GRE, GRE V, GRE AW      | :func:`query_data.getAverageScores`      |
    +-----+---------------------------------------+------------------------------------------+
    | 4   | Average GPA of American Fall 2026     | :func:`query_data.getAmericanGPA`        |
    |     | applicants                            |                                          |
    +-----+---------------------------------------+------------------------------------------+
    | 5   | Fall 2026 acceptance percentage       | :func:`query_data.getFallAcceptancesPercent` |
    +-----+---------------------------------------+------------------------------------------+
    | 6   | Average GPA of Fall 2026 acceptances  | :func:`query_data.getFallAcceptancesGPA` |
    +-----+---------------------------------------+------------------------------------------+
    | 7   | JHU CS master's entry count           | :func:`query_data.getJHUCSEntries`       |
    +-----+---------------------------------------+------------------------------------------+
    | 8   | CS PhD acceptances at Georgetown,     | :func:`query_data.getUniversityListAcceptances` |
    |     | MIT, Stanford, CMU (raw fields)       |                                          |
    +-----+---------------------------------------+------------------------------------------+
    | 9   | Same as Q8 using LLM-generated fields | :func:`query_data.getLLMUniversityListAcceptances` |
    +-----+---------------------------------------+------------------------------------------+
    | 10  | GRE AW scores exceeding maximum       | :func:`query_data.getBadGREAWScores`     |
    +-----+---------------------------------------+------------------------------------------+
    | 11  | GRE scores exceeding maximum          | :func:`query_data.getBadGREScores`       |
    +-----+---------------------------------------+------------------------------------------+

    The returned HTML has the following structure per question::

        <ul>
            <li>
                <h4>{question text}</h4>
                <p class="smalltext">Answer: {result}</p>
            </li>
            ...
        </ul>

    :returns: A complete HTML ``<ul>`` fragment containing eleven
              ``<li>`` elements, each with an ``<h4>`` question heading
              and a ``<p class="smalltext">`` answer paragraph.
    :rtype: str

    :raises psycopg.OperationalError: If the database connection cannot
                                      be established using the
                                      module-level ``config`` dictionary.
    :raises psycopg.DatabaseError: If any delegated query raises a
                                   database-level error during execution.
    :raises IndexError: If a query returns ``None`` or an empty row
                        rather than the expected tuple, causing
                        ``[0]`` indexing to fail.

    .. note::
        All eleven queries share a single connection for the lifetime
        of this function. The connection is closed automatically when
        the ``with`` block exits, whether or not an exception occurs.

    .. note::
        The returned string is an HTML fragment, not a complete document.
        It is intended to be embedded directly into a Jinja2 template
        via ``{{ result | safe }}`` or equivalent. Ensure the calling
        template trusts this output, as the query results are sourced
        from the database and not user input.

    .. seealso::
        :func:`getStats` — the stdout equivalent of this function,
        executing the same eleven queries and printing results to the
        console rather than returning HTML.
    """
    with psycopg.connect(**config) as conn:
        q1Answer = query_data.getTermCount(conn)[0]
        q2Answer = query_data.getInternationalAverage(conn)[0]
        q3Rows = query_data.getAverageScores(conn)
        q3Answer = f"GPA: {q3Rows[0]}, GRE: {q3Rows[1]}, GRE-V: {q3Rows[2]}, GRE-AW: {q3Rows[3]}"
        q4Answer = query_data.getAmericanGPA(conn)[0]
        q5Answer = query_data.getFallAcceptancesPercent(conn)[0]
        q6Answer = query_data.getFallAcceptancesGPA(conn)[0]
        q7Answer = query_data.getJHUCSEntries(conn)[0]
        q8Answer = query_data.getUniversityListAcceptances(conn)[0]
        q9Answer = query_data.getLLMUniversityListAcceptances(conn)[0]
        q10Answer = query_data.getBadGREAWScores(conn)[0]
        q11Answer = query_data.getBadGREScores(conn)[0]

    return f"""<ul>
            <li>
                <h4>1. How many entries do you have in your database who have applied for Fall 2026?</h4>
                <p class="smalltext">Answer: {q1Answer}</p>
            </li>
            <li>
                <h4>2. What percentage of entries are from international students (not American or Other) (to two decimal places)?</h4>
                <p class="smalltext">Answer: {q2Answer}</p>
            </li>
            <li>
                <h4>3. What is the average GPA, GRE, GRE V, GRE AW of applicants who provide these metrics?</h4>
                <p class="smalltext">Answer: {q3Answer}</p>
            </li>
            <li>
                <h4>4. What is their average GPA of American students in Fall 2026?</h4>
                <p class="smalltext">Answer: {q4Answer}</p>
            </li>
            <li>
                <h4>5. What percent of entries for Fall 2026 are Acceptances (to two decimal places)?</h4>
                <p class="smalltext">Answer: {q5Answer}</p>
            </li>
            <li>
                <h4>6. What is the average GPA of applicants who applied for Fall 2026 who are Acceptances?</h4>
                <p class="smalltext">Answer: {q6Answer}</p>
            </li>
            <li>
                <h4>7. How many entries are from applicants who applied to JHU for a masters degrees in Computer Science?</h4>
                <p class="smalltext">Answer: {q7Answer}</p>
            </li>
            <li>
                <h4>8. How many entries from 2026 are acceptances from applicants who applied to Georgetown University, MIT, Stanford University, or Carnegie Mellon University for a PhD in Computer Science?</h4>
                <p class="smalltext">Answer: {q8Answer}</p>
            </li>
            <li>
                <h4>9. Do you numbers for question 8 change if you use LLM Generated Fields (rather than your downloaded fields)?</h4>
                <p class="smalltext">Answer: {q9Answer}</p>
            </li>
            <li>
                <h4>10. How many GRE AW scores reported exceeded the maximum score attainable?</h4>
                <p class="smalltext">Answer: {q10Answer}</p>
            </li>
            <li>
                <h4>11. How many GRE scores reported exceeded the maximum score attainable?</h4>
                <p class="smalltext">Answer: {q11Answer}</p>
            </li>
        </ul>"""

@bp.route('/')
def home():
    """
    Render the application home page.

    Handles HTTP GET requests to the root URL ``/`` and returns the
    rendered ``base.html`` Jinja2 template.

    **Route:**

    +----------+--------+------------------------------------------+
    | URL      | Method | Description                              |
    +==========+========+==========================================+
    | ``/``    | GET    | Serves the application home page        |
    +----------+--------+------------------------------------------+

    :returns: A Flask ``Response`` object containing the rendered
              ``base.html`` template with a ``200 OK`` status.
    :rtype: flask.Response

    :raises jinja2.TemplateNotFound: If ``base.html`` cannot be located
                                     in the configured template folder.

    .. note::
        Registered on the module-level Blueprint ``bp``. Ensure ``bp``
        is registered with the Flask application instance via
        :func:`create_app` before this route becomes accessible.
    """
    return render_template("base.html")

@bp.route('/api/pull-data', methods=['POST'])
def updateDatabase():
    """
    Trigger a background database update by scraping new application
    data from the source site.

    Handles HTTP POST requests to ``/api/pull-data``. If an update is
    already in progress, returns a ``409 Conflict`` response immediately.
    Otherwise, sets the module-level ``updating`` flag, scrapes and
    inserts any new records, then clears the flag on completion.

    **Route:**

    +--------------------+--------+--------------------------------------+
    | URL                | Method | Description                          |
    +====================+========+======================================+
    | ``/api/pull-data`` | POST   | Initiates a database update scrape   |
    +--------------------+--------+======================================+

    **Responses:**

    +-----+-------------------------------+----------------------------------+
    | Code| Condition                     | Body                             |
    +=====+===============================+==================================+
    | 200 | Update completed successfully | ``{"status": "Updated",          |
    |     |                               | "busy": False}``                 |
    +-----+-------------------------------+----------------------------------+
    | 409 | Update already in progress    | ``{"status": "Updating",         |
    |     |                               | "busy": True}``                  |
    +-----+-------------------------------+----------------------------------+

    :returns: A JSON response dict and an HTTP status code. Returns
              ``409`` if ``updating`` is ``True`` at the time of the
              request, or ``200`` on successful completion.
    :rtype: tuple[dict, int]

    :raises psycopg.OperationalError: If the database connection cannot
                                      be established during the insert
                                      phase.
    :raises requests.exceptions.RequestException: If the HTTP request
                                                  to the source site
                                                  fails during scraping.

    .. note::
        Uses the module-level boolean ``updating`` as a concurrency
        guard. This flag is not thread-safe — if the Flask development
        server is run with threading enabled, or if a production WSGI
        server spawns multiple workers, two simultaneous POST requests
        could both read ``updating`` as ``False`` and proceed
        concurrently. Consider replacing with a thread lock
        (``threading.Lock``) or a distributed lock for production use.

    .. warning::
        If an unhandled exception occurs mid-update, ``updating`` may
        be left as ``True``, permanently blocking future requests until
        the server is restarted. Wrap the scrape-and-insert logic in a
        ``try/finally`` block to ensure the flag is always cleared.
    """
    global updating
    # If updating, send blocking response
    if updating:
        return {"status": "Updating",
                "busy": True}, 409
    
    updating = True
    
    lastIDFetched = 1
    with psycopg.connect(**config) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(p_id) FROM applicants")
            lastIDFetched = cur.fetchone()[0] # Mark where we left off last time
    
    scrapedData = scrape.scrape_data(lastIDFetched)

    # If there were new entries, update the database, update the last ID (which should be the first item in the list)
    if scrapedData != None:
        if len(scrapedData) > 0:
            load_data.insertEntries(scrapedData)
            lastIDFetched = scrapedData[0]["id"]

    updating = False
    return {"status": "Available",
            "maxID": f"{lastIDFetched}"}

@bp.route('/api/analysis', methods=['GET'])
def updateAnalysis():
    """
    Trigger a background database update by scraping new application
    data from the source site.

    Handles HTTP POST requests to ``/api/pull-data``. If an update is
    already in progress, returns a ``409 Conflict`` response immediately.
    Otherwise, sets the module-level ``updating`` flag, scrapes and
    inserts any new records, then clears the flag on completion.

    **Route:**

    +--------------------+--------+--------------------------------------+
    | URL                | Method | Description                          |
    +====================+========+======================================+
    | ``/api/pull-data`` | POST   | Initiates a database update scrape   |
    +--------------------+--------+======================================+

    **Responses:**

    +-----+-------------------------------+----------------------------------+
    | Code| Condition                     | Body                             |
    +=====+===============================+==================================+
    | 200 | Update completed successfully | ``{"status": "Updated",          |
    |     |                               | "busy": False}``                 |
    +-----+-------------------------------+----------------------------------+
    | 409 | Update already in progress    | ``{"status": "Updating",         |
    |     |                               | "busy": True}``                  |
    +-----+-------------------------------+----------------------------------+

    :returns: A JSON response dict and an HTTP status code. Returns
              ``409`` if ``updating`` is ``True`` at the time of the
              request, or ``200`` on successful completion.
    :rtype: tuple[dict, int]

    :raises psycopg.OperationalError: If the database connection cannot
                                      be established during the insert
                                      phase.
    :raises requests.exceptions.RequestException: If the HTTP request
                                                  to the source site
                                                  fails during scraping.

    .. note::
        Uses the module-level boolean ``updating`` as a concurrency
        guard. This flag is not thread-safe — if the Flask development
        server is run with threading enabled, or if a production WSGI
        server spawns multiple workers, two simultaneous POST requests
        could both read ``updating`` as ``False`` and proceed
        concurrently. Consider replacing with a thread lock
        (``threading.Lock``) or a distributed lock for production use.

    .. warning::
        If an unhandled exception occurs mid-update, ``updating`` may
        be left as ``True``, permanently blocking future requests until
        the server is restarted. Wrap the scrape-and-insert logic in a
        ``try/finally`` block to ensure the flag is always cleared.
    """
    global updating

    # If updating the database, send blocking response
    if updating:
        return {"status": "Updating",
                "busy": True}, 409

    # Else, build the HTML and send it out
    returnHTML = getAnalysisHTML()
    
    return { "ok": True,
            "status": "Available",
            "content": returnHTML}