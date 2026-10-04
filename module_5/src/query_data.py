"""
Descriptive statistics queries for the GradCafe applicants database.

This module defines a set of parameterless SQL query strings and
corresponding accessor functions that compute descriptive statistics
over an ``applicants`` table (presumably populated by a companion
scraping/cleaning pipeline), plus a top-level :func:`get_stats`
function that opens a database connection, runs all of the queries in
sequence, and prints a human-readable report to stdout.

Each query answers a specific analytical question about the Fall 2026
graduate application dataset -- entry counts, applicant demographics,
score averages, university-specific acceptance rates, and data-quality
checks for out-of-range test scores.

**Module contents:**

+--------------------------------------+--------------------------------------------+
| Name                                  | Description                               |
+========================================+==========================================+
| :data:`TERM_COUNT_SQL` (Q1)           | Count of Fall 2026 entries                |
+--------------------------------------+--------------------------------------------+
| :data:`PERCENT_INTERNATIONAL_SQL` (Q2)| Percent of international applicants       |
+--------------------------------------+--------------------------------------------+
| :data:`AVERAGE_SCORES_SQL` (Q3)       | Average GPA / GRE / GRE V / GRE AW        |
+--------------------------------------+--------------------------------------------+
| :data:`AVERAGE_AMERICAN_GPA_SQL` (Q4) | Average GPA, American, Fall 2026          |
+--------------------------------------+--------------------------------------------+
| :data:`PERCENT_ACCEPTED_SQL` (Q5)     | Acceptance percentage, Fall 2026          |
+--------------------------------------+--------------------------------------------+
| :data:`AVERAGE_GPA_FALL_ACCEPTANCE_SQL` (Q6) | Average GPA, accepted, Fall 2026   |
+--------------------------------------+--------------------------------------------+
| :data:`JHU_APPLICANTS_SQL` (Q7)       | Count of JHU CS Master's entries          |
+--------------------------------------+--------------------------------------------+
| :data:`UNI_LIST_ACCEPTANCE_SQL` (Q8)  | 2026 CS PhD acceptances, target schools   |
|                                        | (raw fields)                             |
+--------------------------------------+--------------------------------------------+
| :data:`LLM_UNI_LIST_ACCEPTANCE_SQL` (Q9) | Same as Q8, LLM-normalised fields      |
+--------------------------------------+--------------------------------------------+
| :data:`BAD_GRE_AW_SCORE_SQL` (Q10)    | Count of out-of-range GRE AW scores       |
+--------------------------------------+--------------------------------------------+
| :data:`BAD_GRE_SCORES_SQL` (Q11)      | Count of out-of-range GRE scores          |
+--------------------------------------+--------------------------------------------+
| :func:`get_term_count`                | Run Q1                                    |
+--------------------------------------+--------------------------------------------+
| :func:`get_international_average`    | Run Q2                                     |
+--------------------------------------+--------------------------------------------+
| :func:`get_average_scores`           | Run Q3                                     |
+--------------------------------------+--------------------------------------------+
| :func:`get_american_gpa`             | Run Q4                                     |
+--------------------------------------+--------------------------------------------+
| :func:`get_fall_acceptance_percent`  | Run Q5                                     |
+--------------------------------------+--------------------------------------------+
| :func:`get_fall_acceptance_gpa`      | Run Q6                                     |
+--------------------------------------+--------------------------------------------+
| :func:`get_jhu_cs_entries`           | Run Q7                                     |
+--------------------------------------+--------------------------------------------+
| :func:`get_uni_acceptances`          | Run Q8                                     |
+--------------------------------------+--------------------------------------------+
| :func:`get_llm_uni_acceptances`      | Run Q9                                     |
+--------------------------------------+--------------------------------------------+
| :func:`get_bad_gre_aw_scores`        | Run Q10                                    |
+--------------------------------------+--------------------------------------------+
| :func:`get_bad_gre_scores`           | Run Q11                                    |
+--------------------------------------+--------------------------------------------+
| :func:`get_stats`                    | Open a connection, run all queries, print  |
|                                        | results                                  |
+--------------------------------------+--------------------------------------------+

**Dependencies:**

* :mod:`psycopg` -- third-party (psycopg 3), used to open the database
  connection and execute SQL.
* :mod:`src.config` -- local module, supplies ``config``, a mapping of
  connection parameters passed to :func:`psycopg.connect` via
  ``get_config()``.

**Implicit schema assumptions:**

This module assumes an ``applicants`` table with at least the
following columns: ``p_id``, ``term``, ``us_or_international``,
``gpa``, ``gre``, ``gre_v``, ``gre_aw``, ``status``, ``university``,
``program``, ``degree``, ``date_added``, ``llm_generated_university``,
and ``llm_generated_program``. No schema migration or table-creation
logic is included in this module; the table is assumed to already
exist and be populated.

.. note::
    Several queries (Q1, Q4, Q5, Q6, Q7, Q8, Q9) hardcode the term
    ``'Fall 2026'`` or the year ``2026`` directly in the SQL string.
    Reusing this module for a different application cycle requires
    editing these query constants rather than passing a parameter.

.. warning::
    Per the docstrings of the delegated query functions, missing
    numeric scores (GPA, GRE, GRE V, GRE AW) are expected to be
    sentinel-coded as ``-1.0`` in the database, and the corresponding
    ``AVERAGE_SCORES_SQL`` / ``AVERAGE_AMERICAN_GPA_SQL`` /
    ``AVERAGE_GPA_FALL_ACCEPTANCE_SQL`` queries filter these out via
    ``> 0`` / ``>= 0`` conditions. If sentinel-coding conventions
    change, these filters must be updated to match.

.. warning::
    :func:`get_stats` contains two call-site bugs: it invokes
    ``get_fall_acceptance_gpa(conn[0])`` and
    ``get_bad_gre_aw_scores(conn[0])``, indexing the connection object
    itself rather than passing ``conn`` and indexing the *result*.
    Since :class:`psycopg.Connection` does not support subscripting,
    both calls will raise :exc:`TypeError` at runtime, causing
    :func:`get_stats` to fail before printing the Q6 and Q10 results.

.. seealso::
    :func:`get_stats` for the aggregate report that ties all query
    functions together, including the printed question text for each
    of the eleven analytical questions.

:Example:

>>> from src import stats
>>> stats.get_stats()
1. How many entries do you have in your database who have applied for Fall 2026?
142
...
"""

import psycopg
from src.config import get_config

# Q1
TERM_COUNT_SQL = """
SELECT COUNT(p_id) AS term_count
FROM applicants
WHERE term = 'Fall 2026'
LIMIT 1;
"""
# Q2
PERCENT_INTERNATIONAL_SQL = """
SELECT
ROUND
    (
        (
            (
                SELECT CAST(COUNT(us_or_international) AS NUMERIC) FROM applicants WHERE us_or_international = 'International'
            )
/
            (
                SELECT CAST(COUNT(us_or_international) AS NUMERIC) FROM applicants
            )
        ) * 100, 2
    )
LIMIT 1;
"""

# Q3
AVERAGE_SCORES_SQL = """
SELECT
    (SELECT AVG(gpa) FROM applicants WHERE gpa > 0) AS avg_gpa,
    (SELECT AVG(gre) FROM applicants WHERE gre > 0) AS avg_gre,
    (SELECT AVG(gre_v) FROM applicants WHERE gre_v > 0) AS avg_gre_v,
    (SELECT AVG(gre_aw) FROM applicants WHERE gre_aw >= 0) AS avg_gre_aw
LIMIT 1;
"""

# Q4
AVERAGE_AMERICAN_GPA_SQL = """
SELECT AVG(gpa)
FROM applicants
WHERE us_or_international = 'American'
    AND gpa > 0
    AND term = 'Fall 2026'
LIMIT 1;
"""

# Q5
PERCENT_ACCEPTED_SQL = """
SELECT
ROUND
    (
        (
            (
                SELECT CAST(COUNT(p_id) AS NUMERIC) FROM applicants WHERE status = 'Accepted' AND term = 'Fall 2026'
            )
/
            (
                SELECT CAST(COUNT(p_id) AS NUMERIC) FROM applicants WHERE term = 'Fall 2026'
            )
        ) * 100, 2
    )
LIMIT 1;
"""

# Q6
AVERAGE_GPA_FALL_ACCEPTANCE_SQL = """
SELECT AVG(gpa)
FROM applicants
WHERE term = 'Fall 2026'
AND status = 'Accepted'
AND gpa > 0
LIMIT 1;
"""

# Q7
JHU_APPLICANTS_SQL = """
SELECT count(p_id)
FROM applicants
WHERE program LIKE '%Computer Science%'
AND university LIKE '%Johns Hopkins%'
AND degree = 'Masters'
LIMIT 1;
"""

# Q8
UNI_LIST_ACCEPTANCE_SQL = """
SELECT COUNT(p_id)
FROM applicants
WHERE extract(YEAR FROM date_added) = 2026
AND degree = 'PhD'
AND program LIKE '%Computer Science%'
AND university LIKE ANY (ARRAY['%Georgetown University%','%Massachusetts Institute of Technology%','%MIT%','%Stanford University%','%Carnegie Mellon%'])
AND status = 'Accepted'
LIMIT 1;
"""

# Q9
LLM_UNI_LIST_ACCEPTANCE_SQL = """
SELECT COUNT(p_id)
FROM applicants
WHERE extract(YEAR FROM date_added) = 2026
AND degree = 'PhD'
AND llm_generated_program LIKE '%Computer Science%'
AND llm_generated_university LIKE ANY (ARRAY['%Georgetown University%','%Massachusetts Institute of Technology%','%MIT%','%Stanford University%','%Carnegie Mellon%'])
AND status = 'Accepted'
LIMIT 1;
"""

# Q10
BAD_GRE_AW_SCORE_SQL = """
SELECT COUNT(p_id)
FROM applicants
WHERE gre_aw > 6
LIMIT 1;
"""

# Q11
BAD_GRE_SCORES_SQL = """
SELECT COUNT(p_id)
FROM applicants
WHERE gre > 340
LIMIT 1;
"""

def get_term_count(conn):
    """
    Query the count of applicant entries for Fall 2026.

    Executes ``TERM_COUNT_SQL`` against the provided database connection
    and returns the first row of the result.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`get_stats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the count of Fall 2026
              entries, e.g. ``(142,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        # Q1
        cur.execute(TERM_COUNT_SQL)
        row = cur.fetchone()
        return row

def get_international_average(conn):
    """
    Query the percentage of applicant entries from international students.

    Executes ``PERCENT_INTERNATIONAL_SQL`` against the provided database
    connection. Excludes applicants categorised as American or Other.
    Returns the percentage rounded to two decimal places.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`get_stats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the international
              applicant percentage, e.g. ``(34.57,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        # Q2
        cur.execute(PERCENT_INTERNATIONAL_SQL)
        row = cur.fetchone()
        return row

def get_average_scores(conn):
    """
    Query the average GPA, GRE, GRE Verbal, and GRE Analytical Writing
    scores across all applicants who reported each metric.

    Executes ``AVERAGE_SCORES_SQL`` against the provided database connection.
    Sentinel values of ``-1.0`` representing missing scores are excluded
    from each average independently, so applicant counts may differ across
    metrics.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`get_stats`.
    :type conn: psycopg.Connection
    :returns: A four-element tuple of the form
              ``(avg_gpa, avg_gre, avg_gre_v, avg_gre_aw)``, e.g.
              ``(3.72, 320.1, 158.4, 4.1)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        # Q3
        cur.execute(AVERAGE_SCORES_SQL)
        row = cur.fetchone()
        return row

def get_american_gpa(conn):
    """
    Query the average GPA of American applicants for Fall 2026.

    Executes ``AVERAGE_AMERICAN_GPA_SQL`` against the provided database
    connection. Filters to applicants whose ``us_or_international``
    field is ``American`` and whose ``term`` is Fall 2026. Excludes
    sentinel GPA values of ``-1.0``.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`get_stats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the average GPA, e.g.
              ``(3.68,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        # Q4
        cur.execute(AVERAGE_AMERICAN_GPA_SQL)
        row = cur.fetchone()
        return row

def get_fall_acceptance_percent(conn):
    """
    Query the percentage of Fall 2026 entries that are acceptances.

    Executes ``PERCENT_ACCEPTED_SQL`` against the provided database
    connection. Filters to entries whose ``term`` is Fall 2026 and
    returns the acceptance rate rounded to two decimal places.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`get_stats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the acceptance
              percentage, e.g. ``(21.43,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        # Q5
        cur.execute(PERCENT_ACCEPTED_SQL)
        row = cur.fetchone()
        return row

def get_fall_acceptance_gpa(conn):
    """
    Query the average GPA of epted applicants for Fall 2026.

    Executes ``AVERAGE_GPA_FALL_ACCEPTANCE_SQL`` against the provided
    database connection. Filters to entries whose ``term`` is Fall 2026
    and whose ``status`` is ``Accepted``. Excludes sentinel GPA values
    of ``-1.0``.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`get_stats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the average GPA of
              accepted Fall 2026 applicants, e.g. ``(3.81,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        # Q6
        cur.execute(AVERAGE_GPA_FALL_ACCEPTANCE_SQL)
        row = cur.fetchone()
        return row

def get_jhu_cs_entries(conn):
    """
    Query the count of entries from applicants who applied to Johns
    Hopkins University for a degree in Computer Science.

    Executes ``JHU_APPLICANTS_SQL`` against the provided database
    connection. Filters on the raw scraped ``university`` and
    ``program`` fields.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`get_stats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the count of matching
              entries, e.g. ``(17,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        # Q7
        cur.execute(JHU_APPLICANTS_SQL)
        row = cur.fetchone()
        return row

def get_uni_acceptances(conn):
    """
    Query the count of 2026 Computer Science acceptances at a fixed
    list of target universities using raw scraped fields.

    Executes ``UNI_LIST_ACCEPTANCE_SQL`` against the provided
    database connection. Filters on the raw scraped ``university`` and
    ``program`` fields for Georgetown University, MIT, Stanford
    University, and Carnegie Mellon University. Compare with
    :func:`get_llm_uni_acceptances` to assess the impact of
    LLM-based name normalisation.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`get_stats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the count of matching
              acceptances, e.g. ``(23,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        # Q8
        cur.execute(UNI_LIST_ACCEPTANCE_SQL)
        row = cur.fetchone()
        return row

def get_llm_uni_acceptances(conn):
    """
    Query the count of 2026 Computer Science acceptances at a fixed
    list of target universities using LLM-generated normalised fields.

    Executes ``LLM_UNI_LIST_ACCEPTANCE_SQL`` against the provided
    database connection. Identical in scope to
    :func:`get_uni_acceptances` but filters on
    ``llm_generated_university`` and ``llm_generated_program`` rather
    than the raw scraped fields. Discrepancies between the two results
    indicate normalisation gaps in the raw data.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`get_stats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the count of matching
              acceptances using LLM-normalised fields, e.g. ``(27,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        # Q9
        cur.execute(LLM_UNI_LIST_ACCEPTANCE_SQL)
        row = cur.fetchone()
        return row

def get_bad_gre_aw_scores(conn):
    """
    Query the count of GRE Analytical Writing scores that exceed the
    maximum attainable score.

    Executes ``BAD_GRE_AW_SCORE_SQL`` against the provided database
    connection. The GRE AW section is scored on a scale of 0.0 to 6.0
    in 0.5 increments; any value above 6.0 is considered invalid. Excludes
    sentinel values of ``-1.0``.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`get_stats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the count of invalid GRE
              AW scores, e.g. ``(4,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        # Q10
        cur.execute(BAD_GRE_AW_SCORE_SQL)
        row = cur.fetchone()
        return row

def get_bad_gre_scores(conn):
    """
    Query the count of GRE total scores that exceed the maximum
    attainable score.

    Executes ``BAD_GRE_SCORES_SQL`` against the provided database
    connection. The GRE composite score has a maximum of 340 (Verbal
    170 + Quantitative 170); any value above 340 is considered invalid.
    Excludes sentinel values of ``-1.0``.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`get_stats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the count of invalid GRE
              scores, e.g. ``(2,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        # Q11
        cur.execute(BAD_GRE_SCORES_SQL)
        row = cur.fetchone()
        return row

def get_stats():
    """
    Query the database and print a suite of descriptive statistics about
    the scraped graduate application dataset.

    Opens a single database connection using the module-level ``config``
    dictionary and executes eleven predefined analytical queries by
    delegating to dedicated query functions. Results are printed to
    stdout in a numbered format. No value is returned.

    **Queries executed:**

    +-----+-------------------------------------------------+------------------------------------+
    | No. | Question                                        | Delegated to                       |
    +=====+=================================================+====================================+
    | 1   | Count of entries for Fall 2026                  | :func:`get_term_count`             |
    +-----+-------------------------------------------------+------------------------------------+
    | 2   | Percentage of international applicants (to 2    | :func:`get_international_average`  |
    |     | d.p.)                                           |                                    |
    +-----+-------------------------------------------------+------------------------------------+
    | 3   | Average GPA, GRE, GRE V, and GRE AW across all  | :func:`get_average_scores`         |
    |     | applicants who reported each metric             |                                    |
    +-----+-------------------------------------------------+------------------------------------+
    | 4   | Average GPA of American applicants for Fall     | :func:`get_american_gpa`           |
    |     | 2026                                            |                                    |
    +-----+-------------------------------------------------+-------  ---------------------------+
    | 5   | Percentage of Fall 2026 entries that are        | :func:`get_fall_acceptance_percent`|
    |     | acceptances (to 2 d.p.)                         |                                    |
    +-----+-------------------------------------------------+------------------------------------+
    | 6   | Average GPA of accepted Fall 2026 applicants    | :func:`get_fall_acceptance_gpa`    |
    +-----+-------------------------------------------------+------------------------------------+
    | 7   | Count of JHU Computer Science master's degree   | :func:`get_jhu_cs_entries`         |
    |     | entries                                         |                                    |
    +-----+-------------------------------------------------+------------------------------------+
    | 8   | Count of 2026 CS PhD acceptances at Georgetown, | :func:`get_uni_acceptances`        |
    |     | MIT, Stanford, or Carnegie Mellon (raw scraped  |                                    |
    |     | fields)                                         |                                    |
    +-----+-------------------------------------------------+------------------------------------+
    | 9   | Same as Q8 using LLM-generated university and   | :func:`get_llm_uni_acceptances`    |
    |     | program fields instead of raw scraped fields    |                                    |
    +-----+-------------------------------------------------+------------------------------------+
    | 10  | Count of GRE AW scores exceeding the maximum    | :func:`get_bad_gre_aw_scores`      |
    |     | attainable                                      |                                    |
    +-----+-------------------------------------------------+------------------------------------+
    | 11  | Count of GRE scores exceeding the maximum       | :func:`get_bad_gre_scores`         |
    |     | attainable fields instead of raw scraped fields |                                    |
    +-----+-------------------------------------------------+------------------------------------+

    :returns: None. All output is written to stdout via :func:`print`.
    :rtype: None

    :raises psycopg.OperationalError: If the database connection cannot
                                      be established using the module-level
                                      ``config`` dictionary.
    :raises psycopg.DatabaseError: If any delegated query function
                                   encounters a database-level error
                                   during execution.

    .. note::
        All eleven queries share a single connection opened for the
        lifetime of this function. The connection is automatically closed
        when the ``with`` block exits, whether or not an exception occurs.

    .. note::
        Q8 and Q9 are designed to be compared directly. Q8 filters on
        raw scraped ``university`` and ``program`` fields, while Q9
        filters on ``llm_generated_university`` and
        ``llm_generated_program``. Discrepancies between their results
        indicate normalisation gaps in the raw scraped data.

    .. warning::
        Missing numeric scores (GPA, GRE, GRE V, GRE AW) are
        sentinel-coded as ``-1.0`` in the database. Ensure each
        delegated query function excludes sentinel values from
        aggregations, or averages and counts will be skewed.
    """
    with psycopg.connect(**get_config()) as conn:
        # Q1
        print('1. How many entries do you have in your database who have applied for Fall 2026?')
        print(get_term_count(conn)[0])
        # Q2
        print("""2. What percentage of entries are from international students (not American or
Other) (to two decimal places)?""")
        print(get_international_average(conn)[0])
        # Q3
        print("""3. What is the average GPA, GRE, GRE V, GRE AW of applicants who provide these
metrics?""")
        averages = get_average_scores(conn)
        print(f"GPA: {averages[0]}, GRE: {averages[1]}")
        print(f"GRE V: {averages[2]}, GRE AW: {averages[3]}")
        # Q4
        print('4. What is their average GPA of American students in Fall 2026?')
        print(get_american_gpa(conn)[0])
        # Q5
        print('5. What percent of entries for Fall 2026 are Acceptances (to two decimal places)?')
        print(get_fall_acceptance_percent(conn)[0])
        # Q6
        print("""6. What is the average GPA of applicants who applied for Fall 2026 who are
Acceptances?""")
        print(get_fall_acceptance_gpa(conn)[0])
        # Q7
        print("""7. How many entries are m applicants who applied to JHU for a masters degrees in
Computer Science?""")
        print(get_jhu_cs_entries(conn)[0])
        # Q8
        print("""8. How many entries from 2026 are acceptances from applicants who applied to
Georgetown University, MIT, Stanford University, or Carnegie Mellon University for a
PhD in Computer Science?""")
        print(get_uni_acceptances(conn)[0])
        # Q9
        print("""9. Do you numbers for question 8 change if you use LLM Generated Fields (rather
than your downloaded fields)?""")
        print(get_llm_uni_acceptances(conn)[0])
        # Q10
        print('10. How many GRE AW scores reported exceeded the maximum score attainable?')
        print(get_bad_gre_aw_scores(conn)[0])
        # Q11
        print('11. How many GRE scores reported exceeded the maximum score attainable?')
        print(get_bad_gre_scores(conn)[0])
