"""
Core Flask blueprint: routes, analysis rendering, and task queueing.

This module defines the ``core`` :class:`flask.Blueprint`, which
provides the application's home page, a health check, an HTML-rendering
helper for the eleven analytical statistics, and API endpoints that
queue work for the RabbitMQ worker and report on it.

Write operations (scraping and recomputing analytics) are never run in
the request. Each one is recorded in the ``tasks`` table and published
to RabbitMQ; the endpoint returns ``202`` with a ``task_id`` that the
page polls through ``GET /api/tasks/<task_id>``. The worker updates the
task's status as it runs.

**Module contents:**

+----------------------------+------------------------------------------+
| Name                       | Description                              |
+============================+==========================================+
| :data:`bp`                 | The ``core`` :class:`flask.Blueprint`    |
+----------------------------+------------------------------------------+
| :data:`STALE_AFTER`        | Age at which an unfinished task is       |
|                            | reported as stale                        |
+----------------------------+------------------------------------------+
| :func:`get_analysis_html`  | Build the HTML fragment of all eleven    |
|                            | analytical answers                       |
+----------------------------+------------------------------------------+
| :func:`_queue_task`        | Record a task row and publish it         |
+----------------------------+------------------------------------------+

**Dependencies:**

* :mod:`flask` -- third-party, supplies :class:`~flask.Blueprint`,
  :func:`~flask.render_template` and :func:`~flask.jsonify`.
* :mod:`psycopg` -- third-party, used for short-lived connections to
  read the analysis view and to read and write the ``tasks`` table.
* :mod:`pika` -- third-party, supplies the AMQP exceptions caught when
  publishing fails.
* :mod:`publisher` -- local module, supplies
  :func:`~publisher.publish_task`.

**Module-level objects:**

``bp``
    The ``core`` :class:`flask.Blueprint`, configured with its own
    ``templates`` folder, ``static`` folder, and a static URL prefix
    of ``/core/static``. Must be registered on the Flask application
    (e.g. via an application factory's ``create_app``) before any of
    its routes become reachable.

**Registered routes:**

+--------------------------+--------+--------------------------------------+
| URL                      | Method | Handler                              |
+==========================+========+======================================+
| ``/``, ``/analysis``     | GET    | :func:`home`                         |
+--------------------------+--------+--------------------------------------+
| ``/health``              | GET    | :func:`health`                       |
+--------------------------+--------+--------------------------------------+
| ``/api/pull-data``       | POST   | :func:`update_database`              |
+--------------------------+--------+--------------------------------------+
| ``/api/analysis``        | POST   | :func:`update_analysis`              |
+--------------------------+--------+--------------------------------------+
| ``/api/analysis``        | GET    | :func:`get_analysis`                 |
+--------------------------+--------+--------------------------------------+
| ``/api/tasks/<task_id>`` | GET    | :func:`get_task`                     |
+--------------------------+--------+--------------------------------------+

"""
import os
import math
import re
import uuid
from datetime import timedelta

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

# A task left queued or running this long is reported as stale
STALE_AFTER = timedelta(minutes=30)

INSERT_TASK_SQL = "INSERT INTO tasks (task_id, kind) VALUES (%s, %s);"

FAIL_TASK_SQL = """
    UPDATE tasks SET status = 'failed', error = %s, updated_at = NOW() WHERE task_id = %s;
"""

SELECT_TASK_SQL = """
    SELECT task_id::text, kind, status, error, created_at, updated_at,
           (status IN ('queued', 'running') AND updated_at < NOW() - %s) AS stale
    FROM tasks WHERE task_id = %s;
"""

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

@bp.route('/health')
def health():
    """
    Report that the web service is up and able to serve requests.

    Used by the Docker Compose healthcheck. Intentionally does not touch
    the database or RabbitMQ so that a dependency outage does not mark
    the web container itself as unhealthy.

    **Route:**

    +--------------+--------+------------------------------------------+
    | URL          | Method | Description                              |
    +==============+========+==========================================+
    | ``/health``  | GET    | Liveness check for the web service       |
    +--------------+--------+------------------------------------------+

    :returns: A JSON body with ``status`` set to ``"ok"`` and HTTP ``200``.
    :rtype: tuple[flask.Response, int]
    """
    return jsonify({"status": "ok"}), 200

def _queue_task(kind):
    """
    Record a new task in the ``tasks`` table and publish it to RabbitMQ.

    The row is committed as ``queued`` before publishing, so the worker
    always finds it when the message arrives. If the publish fails, the
    row is marked ``failed`` so it does not sit in ``queued`` forever.

    :param kind: Task type identifier, e.g. ``"scrape_new_data"``.
    :type kind: str
    :returns: A JSON body with ``status`` ``"queued"``, the ``task_id``
              and ``task`` kind, paired with HTTP ``202``; or an
              ``error`` body paired with HTTP ``503`` if the task could
              not be recorded or published.
    :rtype: tuple[flask.Response, int]
    """
    task_id = str(uuid.uuid4())
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            conn.execute(INSERT_TASK_SQL, (task_id, kind))
    except psycopg.Error:
        current_app.logger.exception("Failed to record %s task", kind)
        return jsonify({"error": "task_create_failed"}), 503

    try:
        publish_task(kind, payload={}, task_id=task_id)
    except (exceptions.AMQPConnectionError,
            exceptions.AMQPError,
            exceptions.ChannelClosedByBroker,
            exceptions.UnroutableError,
            exceptions.StreamLostError,
            OSError) as e:  # e.g. broker hostname not resolvable
        current_app.logger.exception("Failed to publish %s", kind)
        try:
            with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
                conn.execute(FAIL_TASK_SQL, (f"Publish failed: {type(e).__name__}", task_id))
        except psycopg.Error:
            current_app.logger.exception("Failed to mark task %s as failed", task_id)
        return jsonify({"error": "publish_failed", "task_id": task_id}), 503

    return jsonify({"status": "queued", "task_id": task_id, "task": kind}), 202

@bp.route('/api/pull-data', methods=['POST'])
def update_database():
    """
    Queue a scrape of new application entries from GradCafe.

    Records a ``scrape_new_data`` task and publishes it for the worker.
    The scrape itself runs asynchronously; poll
    ``GET /api/tasks/<task_id>`` for its outcome.

    **Route:**

    +--------------------+--------+------------------------------------------+
    | URL                | Method | Description                              |
    +====================+========+==========================================+
    | ``/api/pull-data`` | POST   | Queue a scrape task                      |
    +--------------------+--------+------------------------------------------+

    :returns: See :func:`_queue_task`.
    :rtype: tuple[flask.Response, int]
    """
    return _queue_task("scrape_new_data")

@bp.route('/api/analysis', methods=['POST'])
def update_analysis():
    """
    Queue a refresh of the ``compiled_analytics`` materialized view.

    Records a ``recompute_analytics`` task and publishes it for the
    worker. Poll ``GET /api/tasks/<task_id>`` for its outcome, then fetch
    the refreshed answers from ``GET /api/analysis``.

    **Route:**

    +-------------------+--------+------------------------------------------+
    | URL               | Method | Description                              |
    +===================+========+==========================================+
    | ``/api/analysis`` | POST   | Queue an analytics recompute task        |
    +-------------------+--------+------------------------------------------+

    :returns: See :func:`_queue_task`.
    :rtype: tuple[flask.Response, int]
    """
    return _queue_task("recompute_analytics")

@bp.route('/api/analysis', methods=['GET'])
def get_analysis():
    """
    Return the current analysis HTML fragment as JSON.

    Lets the page swap in fresh answers after a recompute task succeeds,
    without a full page reload. Performs no writes.

    **Route:**

    +-------------------+--------+------------------------------------------+
    | URL               | Method | Description                              |
    +===================+========+==========================================+
    | ``/api/analysis`` | GET    | Return the rendered analysis HTML        |
    +-------------------+--------+------------------------------------------+

    :returns: A JSON body with ``content`` set to the HTML fragment from
              :func:`get_analysis_html` and HTTP ``200``, or an ``error``
              body with HTTP ``503`` if the database is unavailable.
    :rtype: tuple[flask.Response, int]
    """
    try:
        return jsonify({"content": get_analysis_html()}), 200
    except psycopg.Error:
        current_app.logger.exception("Failed to read analysis")
        return jsonify({"error": "database_unavailable"}), 503

@bp.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """
    Return the status of a queued task.

    The worker moves a task from ``queued`` to ``running`` and then to
    ``succeeded`` or ``failed``. A task still ``queued`` or ``running``
    after :data:`STALE_AFTER` is flagged ``stale``, which usually means
    the worker died part-way through it.

    **Route:**

    +--------------------------+--------+-----------------------------------+
    | URL                      | Method | Description                       |
    +==========================+========+===================================+
    | ``/api/tasks/<task_id>`` | GET    | Return one task's status          |
    +--------------------------+--------+-----------------------------------+

    :param task_id: The UUID returned when the task was queued.
    :type task_id: str
    :returns: A JSON body with ``task_id``, ``kind``, ``status``,
              ``error``, ``stale``, ``created_at`` and ``updated_at`` and
              HTTP ``200``; HTTP ``404`` if no such task exists; or HTTP
              ``503`` if the database is unavailable.
    :rtype: tuple[flask.Response, int]
    """
    try:
        uuid.UUID(task_id)
    except ValueError:
        return jsonify({"error": "task_not_found"}), 404

    try:
        with psycopg.connect(os.getenv("DATABASE_URL"), row_factory=dict_row) as conn:
            task = conn.execute(SELECT_TASK_SQL, (STALE_AFTER, task_id)).fetchone()
    except psycopg.Error:
        current_app.logger.exception("Failed to read task %s", task_id)
        return jsonify({"error": "database_unavailable"}), 503

    if task is None:
        return jsonify({"error": "task_not_found"}), 404
    task["created_at"] = task["created_at"].isoformat()
    task["updated_at"] = task["updated_at"].isoformat()
    return jsonify(task), 200
