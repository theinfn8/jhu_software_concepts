"""
Core Flask blueprint: routes, analysis rendering, and database refresh.

This module defines the ``core`` :class:`flask.Blueprint`, which
provides the application's home page, an HTML-rendering helper for the
eleven analytical statistics computed elsewhere in the project, and
two API endpoints that respectively trigger a scrape-and-insert
database refresh and return the rendered analysis HTML. A
process-wide :class:`threading.Lock` guards against concurrent
database refreshes.

**Module contents:**

+----------------------------+------------------------------------------+
| Name                       | Description                              |
+============================+==========================================+
| :data:`UPDATING_LOCK`      | Module-level lock guarding concurrent    |
|                             | database refreshes                      |
+----------------------------+------------------------------------------+
| :data:`bp`                 | The ``core`` :class:`flask.Blueprint`    |
+----------------------------+------------------------------------------+
| :func:`get_analysis_html`  | Build the HTML fragment of all eleven    |
|                             | analytical answers                      |
+----------------------------+------------------------------------------+
| :func:`home`               | ``GET /`` -- render the home page        |
+----------------------------+------------------------------------------+
| :func:`update_database`    | ``POST /api/pull-data`` -- scrape and    |
|                             | insert new records                      |
+----------------------------+------------------------------------------+
| :func:`update_analysis`    | ``GET /api/analysis`` -- return rendered |
|                             | analysis HTML as JSON                   |
+----------------------------+------------------------------------------+

**Dependencies:**

* :mod:`threading` -- standard library, supplies :class:`~threading.Lock`
  used as ``UPDATING_LOCK``.
* :mod:`flask` -- third-party, supplies :class:`~flask.Blueprint` and
  :func:`~flask.render_template`.
* :mod:`psycopg` -- third-party, used to open a short-lived connection
  for fetching the last-inserted record ID.
* :mod:`src.query_data` -- local module, supplies the eleven
  statistic-fetching functions invoked by :func:`get_analysis_html`.
* :mod:`src.scrape` -- local module, supplies
  :func:`~src.scrape.scrape_data`, used by :func:`update_database`.
* :mod:`src.load_data` -- local module, supplies
  :func:`~src.load_data.insert_entries`, used by
  :func:`update_database` to persist newly scraped records.
* :mod:`src.config` -- local module, supplies ``config``, the database
  connection parameters used by :func:`get_analysis_html` and
  :func:`update_database`.

**Module-level objects:**

``UPDATING_LOCK``
    A :class:`threading.Lock` instance shared across requests, acquired
    by both :func:`update_database` and :func:`update_analysis` to
    serialise access to the database refresh. Callers check
    ``UPDATING_LOCK.locked()`` first to return an immediate ``409``
    response rather than blocking on a held lock.

``bp``
    The ``core`` :class:`flask.Blueprint`, configured with its own
    ``templates`` folder, ``static`` folder, and a static URL prefix
    of ``/core/static``. Must be registered on the Flask application
    (e.g. via an application factory's ``create_app``) before any of
    its routes become reachable.

**Registered routes:**

+----------------------+--------+------------------------------------------+
| URL                   | Method | Handler                                   |
+=======================+========+============================================+
| ``/``                 | GET    | :func:`home`                              |
+----------------------+--------+------------------------------------------+
| ``/api/pull-data``    | POST   | :func:`update_database`                   |
+----------------------+--------+------------------------------------------+
| ``/api/analysis``     | GET    | :func:`update_analysis`                   |
+----------------------+--------+------------------------------------------+

.. note::
    Despite their names, :func:`update_database` and
    :func:`update_analysis` serve different purposes:
    :func:`update_database` scrapes the source site and persists new
    records (the actual "update"), while :func:`update_analysis`
    performs no database writes -- it only re-renders the analysis
    HTML fragment via :func:`get_analysis_html` under the same lock.

.. warning::
    Within :func:`update_database`, if an exception is raised after
    ``UPDATING_LOCK`` is acquired (e.g. during scraping or insertion),
    the ``with UPDATING_LOCK:`` context manager will still release the
    lock on exit, so the lock itself will not be left permanently held.
    However, any partially completed update (e.g. a successful scrape
    followed by a failed insert) is not rolled back at the application
    level beyond what :func:`~src.load_data.insert_entries`'s own
    transaction handling provides.

.. seealso::
    :mod:`src.query_data` for the eleven underlying statistics
    functions consumed by :func:`get_analysis_html`.

    :func:`src.app.create_app` (or equivalent application factory) for
    where ``bp`` is registered onto the Flask application.
"""
from threading import Lock

from flask import Blueprint, render_template
import psycopg

from src import query_data
from src import scrape
from src import load_data
from src.config import get_config

UPDATING_LOCK = Lock()

bp = Blueprint('core', __name__,
               template_folder="templates",
               static_folder="static",
               static_url_path='/core/static')

def get_analysis_html():
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

    +-----+----------------------------------+----------------------------------------------------+
    | No. | Question summary                 | Delegated to                                       |
    +=====+==================================+====================================================+
    | 1   | Fall 2026 entry count            | :func:`query_data.getTermCount`                    |
    +-----+----------------------------------+----------------------------------------------------+
    | 2   | International applicant          | :func:`query_data.getInternationalAverage`         |
    |     | percentage                       |                                                    |
    +-----+----------------------------------+----------------------------------------------------+
    | 3   | Average GPA, GRE, GRE V, GRE AW  | :func:`query_data.getAverageScores`                |
    +-----+----------------------------------+----------------------------------------------------+
    | 4   | Average GPA of American Fall 2026| :func:`query_data.getAmericanGPA`                  |
    |     | applicants                       |                                                    |
    +-----+----------------------------------+----------------------------------------------------+
    | 5   | Fall 2026 acceptance percentage  | :func:`query_data.getFallAcceptancesPercent`       |
    +-----+----------------------------------+----------------------------------------------------+
    | 6   | Average GPA of Fall 2026         | :func:`query_data.getFallAcceptancesGPA`           |
    |     | acceptances                      |                                                    |
    +-----+----------------------------------+----------------------------------------------------+
    | 7   | JHU CS master's entry count      | :func:`query_data.getJHUCSEntries`                 |
    +-----+----------------------------------+----------------------------------------------------+
    | 8   | CS PhD acceptances at Georgetown,| :func:`query_data.getUniversityListAcceptances`    |
    |     | MIT, Stanford, CMU (raw fields)  |                                                    |
    +-----+----------------------------------+----------------------------------------------------+
    | 9   | Same as Q8 using LLM-generated   | :func:`query_data.getLLMUniversityListAcceptances` |
    |     | fields                           |                                                    |
    +-----+----------------------------------+----------------------------------------------------+
    | 10  | GRE AW scores exceeding maximum  | :func:`query_data.getBadGREAWScores`               |
    +-----+----------------------------------+----------------------------------------------------+
    | 11  | GRE scores exceeding maximum     | :func:`query_data.getBadGREScores`                 |
    +-----+----------------------------------+----------------------------------------------------+

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
    with psycopg.connect(**get_config()) as conn:
        q1_answer = query_data.get_term_count(conn)[0]
        q2_answer = query_data.get_international_average(conn)[0]
        q3_rows = query_data.get_average_scores(conn)
        q3_answer = f"GPA: {q3_rows[0]}, GRE: {q3_rows[1]},"
        q3_answer = q3_answer + f"GRE-V: {q3_rows[2]}, GRE-AW: {q3_rows[3]}"
        q4_answer = query_data.get_american_gpa(conn)[0]
        q5_answer = query_data.get_fall_acceptance_percent(conn)[0]
        q6_answer = query_data.get_fall_acceptance_gpa(conn)[0]
        q7_answer = query_data.get_jhu_cs_entries(conn)[0]
        q8_answer = query_data.get_uni_acceptances(conn)[0]
        q9_answer = query_data.get_llm_uni_acceptances(conn)[0]
        q10_answer = query_data.get_bad_gre_aw_scores(conn)[0]
        q11_answer = query_data.get_bad_gre_scores(conn)[0]

    return f"""<ul>
            <li>
                <h4>1. How many entries do you have in your database who have applied for Fall 2026?</h4>
                <p class="smalltext">Answer: {q1_answer}</p>
            </li>
            <li>
                <h4>2. What percentage of entries are from international students (not American or Other) (to two decimal places)?</h4>
                <p class="smalltext">Answer: {q2_answer}</p>
            </li>
            <li>
                <h4>3. What is the average GPA, GRE, GRE V, GRE AW of applicants who provide these metrics?</h4>
                <p class="smalltext">Answer: {q3_answer}</p>
            </li>
            <li>
                <h4>4. What is their average GPA of American students in Fall 2026?</h4>
                <p class="smalltext">Answer: {q4_answer}</p>
            </li>
            <li>
                <h4>5. What percent of entries for Fall 2026 are Acceptances (to two decimal places)?</h4>
                <p class="smalltext">Answer: {q5_answer}</p>
            </li>
            <li>
                <h4>6. What is the average GPA of applicants who applied for Fall 2026 who are Acceptances?</h4>
                <p class="smalltext">Answer: {q6_answer}</p>
            </li>
            <li>
                <h4>7. How many entries are from applicants who applied to JHU for a masters degrees in Computer Science?</h4>
                <p class="smalltext">Answer: {q7_answer}</p>
            </li>
            <li>
                <h4>8. How many entries from 2026 are acceptances from applicants who applied to Georgetown University, MIT, Stanford University, or Carnegie Mellon University for a PhD in Computer Science?</h4>
                <p class="smalltext">Answer: {q8_answer}</p>
            </li>
            <li>
                <h4>9. Do you numbers for question 8 change if you use LLM Generated Fields (rather than your downloaded fields)?</h4>
                <p class="smalltext">Answer: {q9_answer}</p>
            </li>
            <li>
                <h4>10. How many GRE AW scores reported exceeded the maximum score attainable?</h4>
                <p class="smalltext">Answer: {q10_answer}</p>
            </li>
            <li>
                <h4>11. How many GRE scores reported exceeded the maximum score attainable?</h4>
                <p class="smalltext">Answer: {q11_answer}</p>
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
def update_database():
    """
    Trigger a synchronous database refresh by scraping new application
    entries from the source site and inserting any that are new.

    Handles HTTP POST requests to ``/api/pull-data``. If
    ``UPDATING_LOCK`` is already held by another in-progress request,
    returns an immediate ``409 Conflict`` response without blocking.
    Otherwise, acquires ``UPDATING_LOCK`` for the duration of the
    refresh and performs the following steps:

    1. Opens a short-lived database connection and queries
       ``MAX(p_id)`` from the ``applicants`` table to determine
       ``last_id_fetched``, the most recently stored record ID.
    2. Calls :func:`scrape.scrape_data` with ``last_id_fetched`` to
       fetch any newer entries from the source site.
    3. If new entries were found (``scraped_data`` is not ``None`` and
       non-empty), persists them via :func:`load_data.insert_entries`
       and updates ``last_id_fetched`` to the ID of the first scraped
       record.

    The lock is released automatically when the ``with UPDATING_LOCK:``
    block exits, whether or not an exception occurred.

    **Route:**

    +--------------------+--------+--------------------------------------+
    | URL                | Method | Description                          |
    +====================+========+======================================+
    | ``/api/pull-data`` | POST   | Scrapes and inserts new applicant    |
    |                    |        | records                              |
    +--------------------+--------+--------------------------------------+

    **Responses:**

    +-----+---------------------------------+------------------------------------+
    | Code| Condition                       | Body                                |
    +=====+=================================+======================================+
    | 200 | Refresh completed (with or      | ``{"status": "Available",           |
    |     | without new entries)             | "maxID": "<last_id_fetched>"}``     |
    +-----+---------------------------------+------------------------------------+
    | 409 | A refresh is already in progress| ``{"status": "UPDATING",            |
    |     |                                 | "busy": True}``                     |
    +-----+---------------------------------+------------------------------------+

    :returns: On success, a dict with ``status`` set to ``"Available"``
              and ``maxID`` set to the string-formatted highest known
              ``p_id`` after the refresh (default Flask ``200`` status).
              If a refresh is already underway, a tuple of a dict with
              ``status`` set to ``"UPDATING"`` and ``busy`` set to
              ``True``, paired with HTTP status ``409``.
    :rtype: dict or tuple[dict, int]

    :raises psycopg.OperationalError: If the database connection cannot
                                      be established when querying the
                                      current maximum ``p_id``.
    :raises psycopg.DatabaseError: If the ``MAX(p_id)`` query or the
                                   subsequent insert fails at the
                                   database level.
    :raises Exception: Any unhandled exception raised by
                       :func:`scrape.scrape_data` or
                       :func:`load_data.insert_entries` propagates to
                       the caller uncaught; the lock is still released
                       via the ``with`` statement, but no response body
                       is returned to the client in that case.

    .. note::
        ``maxID`` in the response reflects the ID of the *first*
        scraped record (assumed to be the newest, per
        :func:`scrape.scrape_data`'s newest-first ordering) when new
        data was found, or the pre-refresh ``MAX(p_id)`` value
        otherwise.

    .. warning::
        Concurrency is guarded by ``UPDATING_LOCK``
        (:class:`threading.Lock`), which only provides mutual
        exclusion within a single process. Running multiple WSGI
        worker processes will allow simultaneous refreshes across
        processes, each with its own independent lock instance.

    .. seealso::
        :func:`scrape.scrape_data` for how new entries are fetched and
        how pagination/termination against ``last_id_fetched`` is
        handled.

        :func:`load_data.insert_entries` for how scraped records are
        converted and persisted.
    """

    if UPDATING_LOCK.locked():
        # If updating, send blocking response
        return {"status": "UPDATING",
                "busy": True}, 409

    with UPDATING_LOCK:

        last_id_fetched = 1
        with psycopg.connect(**get_config()) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(p_id) FROM applicants")
                last_id_fetched = cur.fetchone()[0] # Mark where we left off last time

        scraped_data = scrape.scrape_data(last_id_fetched)

        # If there were new entries, update the database, update the last ID
        # (which should be the first item in the list)
        if scraped_data is not None:
            if len(scraped_data) > 0:
                load_data.insert_entries(scraped_data)
                last_id_fetched = scraped_data[0]["id"]

    return {"status": "Available",
            "maxID": f"{last_id_fetched}"}

@bp.route('/api/analysis', methods=['GET'])
def update_analysis():
    """
    Return the rendered analysis HTML fragment as a JSON response.

    Handles HTTP GET requests to ``/api/analysis``. If
    ``UPDATING_LOCK`` is currently held (e.g. a database refresh
    triggered by :func:`update_database` is in progress), returns an
    immediate ``409 Conflict`` response without blocking. Otherwise,
    acquires ``UPDATING_LOCK`` for the duration of the call, builds the
    analysis HTML via :func:`get_analysis_html`, and returns it
    wrapped in a JSON body.

    This endpoint performs no database writes; it shares
    ``UPDATING_LOCK`` with :func:`update_database` purely to avoid
    rendering analysis HTML concurrently with an in-progress data
    refresh (e.g. to avoid querying a table mid-insert).

    **Route:**

    +-------------------+--------+----------------------------------------+
    | URL                | Method | Description                           |
    +====================+========+=======================================+
    | ``/api/analysis`` | GET    | Returns the rendered analysis HTML     |
    +-------------------+--------+----------------------------------------+

    **Responses:**

    +-----+---------------------------------+----------------------------------------------+
    | Code| Condition                       | Body                                         |
    +=====+=================================+==============================================+
    | 200 | Analysis HTML built successfully| ``{"ok": True, "status": "Available",        |
    |     |                                 | "content": "<ul>...</ul>"}``                 |
    +-----+---------------------------------+----------------------------------------------+
    | 409 | A database refresh is currently | ``{"status": "UPDATING", "busy": True}``     |
    |     | in progress                     |                                              |
    +-----+---------------------------------+----------------------------------------------+

    :returns: On success, a dict with ``ok`` set to ``True``, ``status``
              set to ``"Available"``, and ``content`` set to the HTML
              fragment returned by :func:`get_analysis_html` (default
              Flask ``200`` status). If a refresh is in progress, a
              tuple of a dict with ``status`` set to ``"UPDATING"`` and
              ``busy`` set to ``True``, paired with HTTP status ``409``.
    :rtype: dict or tuple[dict, int]

    :raises psycopg.OperationalError: If :func:`get_analysis_html`
                                      cannot establish its database
                                      connection.
    :raises psycopg.DatabaseError: If any of the eleven underlying
                                   statistics queries invoked by
                                   :func:`get_analysis_html` fail at
                                   the database level.
    :raises IndexError: If any underlying query returns an empty or
                        unexpected row, propagated from
                        :func:`get_analysis_html`.

    .. seealso::
        :func:`get_analysis_html` for how the eleven statistics are
        queried and assembled into the returned HTML fragment.

        :func:`update_database` for the counterpart endpoint that
        shares ``UPDATING_LOCK`` and actually mutates the database.
    """

    if UPDATING_LOCK.locked():
        # If updating the database, send blocking response
        return {"status": "UPDATING",
                "busy": True}, 409

    with UPDATING_LOCK:
        # Else, build the HTML and send it out
        return_html = get_analysis_html()

    return { "ok": True,
            "status": "Available",
            "content": return_html}
