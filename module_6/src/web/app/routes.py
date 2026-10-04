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

"""
import os
import math
import re

from flask import Blueprint, render_template, jsonify, current_app
import psycopg
from psycopg.rows import dict_row
from pika import exceptions

from publisher import publish_task
#from src.config import get_config

bp = Blueprint('core', __name__,
               template_folder="templates",
               static_folder="static",
               static_url_path='/core/static')

def format_number(n: float) -> str:
    """Returns a number to exactly two decimal places."""
    truncated = math.floor(n * 100) / 100
    return f"{truncated:.2f}"

def format_numbers_in_string(text: str) -> str:
    """Replaces all numbers in a string with two decimal place versions."""
    return re.sub(r'-?\d+\.?\d*', lambda m: format_number(float(m.group())), text)

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

    """
    with psycopg.connect(os.getenv("DATABASE_URL"),row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            view_select_sql = "SELECT * FROM compiled_analytics"
            cur.execute(view_select_sql)
            answers = cur.fetchone()
            q3_answer = f"GPA: {answers['average_gpa']}, \
GRE: {answers['average_gre']}, \
GRE-V: {answers['average_grev']}, \
GRE-AW: {answers['average_gre_aw']}"

    return f"""<ul>
            <li>
                <h4>1. How many entries do you have in your database who have applied for Fall
                2026?</h4>
                <p class="smalltext">Answer: {answers["term_count"]}</p>
            </li>
            <li>
                <h4>2. What percentage of entries are from international students (not American or 
                Other) (to two decimal places)?</h4>
                <p class="smalltext">Answer:
                {format_numbers_in_string(str(answers["percent_international"]))}</p>
            </li>
            <li>
                <h4>3. What is the average GPA, GRE, GRE V, GRE AW of applicants who provide these
                    metrics?</h4>
                <p class="smalltext">Answer: {q3_answer}</p>
            </li>
            <li>
                <h4>4. What is their average GPA of American students in Fall 2026?</h4>
                <p class="smalltext">Answer: {answers['average_american_gpa']}</p>
            </li>
            <li>
                <h4>5. What percent of entries for Fall 2026 are Acceptances (to two decimal
                places)?</h4>
                <p class="smalltext">Answer: 
                {format_numbers_in_string(str(answers['percent_accepted']))}</p>
            </li>
            <li>
                <h4>6. What is the average GPA of applicants who applied for Fall 2026 who are
                Acceptances?</h4>
                <p class="smalltext">Answer: {answers['average_gpa_fall_acceptance']}</p>
            </li>
            <li>
                <h4>7. How many entries are from applicants who applied to JHU for a masters
                degrees in Computer Science?</h4>
                <p class="smalltext">Answer: {answers['jhu_applicants']}</p>
            </li>
            <li>
                <h4>8. How many entries from 2026 are acceptances from applicants who applied to
                Georgetown University, MIT, Stanford University, or Carnegie Mellon University for
                a PhD in Computer Science?</h4>
                <p class="smalltext">Answer: {answers['uni_list_acceptance']}</p>
            </li>
            <li>
                <h4>9. Do you numbers for question 8 change if you use LLM Generated Fields (rather
                than your downloaded fields)?</h4>
                <p class="smalltext">Answer: {answers['llm_uni_list_acceptance']}</p>
            </li>
            <li>
                <h4>10. How many GRE AW scores reported exceeded the maximum score attainable?</h4>
                <p class="smalltext">Answer: {answers['bad_gre_aw_scores']}</p>
            </li>
            <li>
                <h4>11. How many GRE scores reported exceeded the maximum score attainable?</h4>
                <p class="smalltext">Answer: {answers['bad_gre_scores']}</p>
            </li>
        </ul>"""

@bp.route('/')
@bp.route('/analysis')
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
    """
    analysis = get_analysis_html()
    # print(analysis)
    return render_template("index.html", analysis_html=analysis)

@bp.route('/api/pull-data', methods=['POST'])
def update_database():
    """
    Trigger a synchronous database refresh by scraping new application
    entries from the source site and inserting any that are new.

    :returns: On success, a dict with ``status`` set to ``"Available"``
              and ``maxID`` set to the string-formatted highest known
              ``p_id`` after the refresh (default Flask ``200`` status).
              If a refresh is already underway, a tuple of a dict with
              ``status`` set to ``"UPDATING"`` and ``busy`` set to
              ``True``, paired with HTTP status ``409``.
    :rtype: dict or tuple[dict, int]
"""

    try:
        publish_task("scrape_new_data", payload={})
        return jsonify({"status":"queued", "task":"scrape_new_data"}), 202
    except (exceptions.AMQPConnectionError,
            exceptions.AMQPError,
            exceptions.ChannelClosedByBroker,
            exceptions.UnroutableError,
            exceptions.StreamLostError):
        current_app.logger.exception("Failed to publish recompute_analytics")
        return jsonify({"error":"publish_failed"}), 503

@bp.route('/api/analysis', methods=['POST'])
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

    :returns: On success, a dict with ``ok`` set to ``True``, ``status``
              set to ``"Available"``, and ``content`` set to the HTML
              fragment returned by :func:`get_analysis_html` (default
              Flask ``200`` status). If a refresh is in progress, a
              tuple of a dict with ``status`` set to ``"UPDATING"`` and
              ``busy`` set to ``True``, paired with HTTP status ``409``.
    :rtype: dict or tuple[dict, int]
    """

    try:
        publish_task("recompute_analytics", payload={})
        return jsonify({"status":"queued","task":"recompute_analytics"}), 202
    except (exceptions.AMQPConnectionError,
            exceptions.AMQPError,
            exceptions.ChannelClosedByBroker,
            exceptions.UnroutableError,
            exceptions.StreamLostError):
        current_app.logger.exception("Failed to publish recompute_analytics")
        return jsonify({"error":"publish_failed"}), 503
