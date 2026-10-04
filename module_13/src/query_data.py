"""
Descriptive statistics queries for the GradCafe applicants database.

This module defines a set of parameterized SQL query templates (built
with :mod:`psycopg.sql` composition rather than raw strings) and
corresponding accessor functions that compute descriptive statistics
over an ``applicants`` table, plus a top-level :func:`get_stats`
function that opens a database connection, runs all of the queries in
sequence, and prints a human-readable report to stdout.

**Why psycopg SQL composition, even for values that are currently
constant:** every query here builds its statement via
:func:`psycopg.sql.SQL` / :class:`psycopg.sql.Identifier`, and every
comparison value (term, year, GRE thresholds, university list) is
passed as a bound parameter rather than interpolated into the SQL
text -- even the ones that happen to be hardcoded defaults today. This
keeps table/column identifiers safely quoted, keeps values out of the
SQL string entirely (so there is no string-built SQL to harden later
if any of these ever become user-supplied, e.g. a term-selector on the
web page), and removes the previous hardcoding of ``'Fall 2026'`` /
``2026`` as literal SQL text -- they are now function default
arguments instead, so reusing this module for a new application cycle
means calling with a different ``term``/``year``, not editing SQL
strings.

**Module contents:**

+--------------------------------------+--------------------------------------------+
| Name                                  | Description                               |
+========================================+==========================================+
| :data:`APPLICANTS_TABLE`              | Composed table identifier                 |
+--------------------------------------+--------------------------------------------+
| :data:`GRE_MAX` / :data:`GRE_AW_MAX`  | Maximum attainable GRE / GRE AW scores    |
+--------------------------------------+--------------------------------------------+
| :data:`TARGET_UNIVERSITIES`           | Default university list for Q8/Q9         |
+--------------------------------------+--------------------------------------------+
| :func:`clamp_limit`                   | Clamp a user-supplied LIMIT into a safe   |
|                                        | range                                     |
+--------------------------------------+--------------------------------------------+
| :func:`get_term_count` ... :func:`get_bad_gre_scores` | Q1-Q11 accessor functions |
+--------------------------------------+--------------------------------------------+
| :func:`get_recent_entries`            | User-facing, limit-bounded query (new)    |
+--------------------------------------+--------------------------------------------+
| :func:`get_stats`                     | Open a connection, run all Q1-Q11 queries,|
|                                        | print results                             |
+--------------------------------------+--------------------------------------------+

**Dependencies:**

* :mod:`psycopg` -- third-party (psycopg 3); ``psycopg.sql`` supplies
  the composition primitives (:func:`~psycopg.sql.SQL`,
  :class:`~psycopg.sql.Identifier`) used throughout this module.
* :mod:`src.config` -- local module, supplies ``config`` via
  ``get_config()``.

**Implicit schema assumptions:**

This module assumes an ``applicants`` table with at least the
following columns: ``p_id``, ``term``, ``us_or_international``,
``gpa``, ``gre``, ``gre_v``, ``gre_aw``, ``status``, ``university``,
``program``, ``degree``, ``date_added``, ``llm_generated_university``,
and ``llm_generated_program``.

.. warning::
    Per the docstrings of the delegated query functions, missing
    numeric scores (GPA, GRE, GRE V, GRE AW) are expected to be
    sentinel-coded as ``-1.0`` in the database, and the corresponding
    ``AVERAGE_SCORES_SQL`` / ``AVERAGE_AMERICAN_GPA_SQL`` /
    ``AVERAGE_GPA_FALL_ACCEPTANCE_SQL`` queries filter these out via
    the module-level :data:`SENTINEL_MISSING` constant, bound as a
    query parameter.

.. seealso::
    :func:`get_stats` for the aggregate report that ties all query
    functions together, including the printed question text for each
    of the eleven analytical questions.
"""

from dataclasses import dataclass, field

import psycopg
from psycopg import sql

from src.config import get_config

APPLICANTS_TABLE = sql.Identifier("applicants")

# Missing numeric scores are sentinel-coded as -1.0 in the database
# (see src.load_data). Bound as a query parameter rather than a magic
# number embedded in each SQL string.
SENTINEL_MISSING = -1.0

# Maximum attainable scores, used to flag data-quality outliers (Q10/Q11).
GRE_AW_MAX = 6
GRE_MAX = 340

# Default filter values. Previously hardcoded directly into each SQL
# string; now plain function defaults, so a new application cycle only
# requires calling these functions with a different term/year rather
# than editing query text.
DEFAULT_TERM = "Fall 2026"
DEFAULT_YEAR = 2026
DEFAULT_INTERNATIONAL_LABEL = "International"

TARGET_UNIVERSITIES = [
    "%Georgetown University%",
    "%Massachusetts Institute of Technology%",
    "%MIT%",
    "%Stanford University%",
    "%Carnegie Mellon%",
]


@dataclass
class AcceptanceQueryParams:
    """Bundled filter values for :func:`get_uni_acceptances` /
    :func:`get_llm_uni_acceptances` (Q8/Q9), so those functions take a
    single parameter object rather than five separate arguments.

    :param year: The ``date_added`` year to filter on.
    :type year: int
    :param degree: The degree type to filter on.
    :type degree: str
    :param program_pattern: ``LIKE`` pattern for the program name.
    :type program_pattern: str
    :param universities: ``LIKE`` patterns to match against the
        university field.
    :type universities: list[str]
    :param status: The status value counted as an acceptance.
    :type status: str
    """
    year: int = DEFAULT_YEAR
    degree: str = "PhD"
    program_pattern: str = "%Computer Science%"
    universities: list = field(default_factory=lambda: list(TARGET_UNIVERSITIES))
    status: str = "Accepted"

# LIMIT bounds for any user-facing, limit-taking query (see
# :func:`clamp_limit` and :func:`get_recent_entries`).
MIN_LIMIT = 1
MAX_LIMIT = 100
DEFAULT_LIMIT = 20


def clamp_limit(value, minimum=MIN_LIMIT, maximum=MAX_LIMIT, default=DEFAULT_LIMIT):
    """Clamp a (possibly user-supplied) LIMIT value into a safe range.

    Any value that can't be parsed as an integer falls back to
    ``default`` rather than raising, since this is meant to sit
    directly in front of untrusted request input (e.g. a query string
    parameter) where a malformed or missing value should degrade
    gracefully rather than crash the request.

    :param value: The requested limit, e.g. from
        ``request.args.get("limit")``. May be a string, int, ``None``,
        or any other type.
    :param minimum: The smallest allowed limit.
    :type minimum: int
    :param maximum: The largest allowed limit.
    :type maximum: int
    :param default: The value to use if ``value`` can't be parsed.
    :type default: int
    :return: An integer guaranteed to be within ``[minimum, maximum]``.
    :rtype: int

    :Example:

    >>> clamp_limit("20")
    20
    >>> clamp_limit("99999")
    100
    >>> clamp_limit("-5")
    1
    >>> clamp_limit("not-a-number")
    20
    """
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(parsed, maximum))


# --- Q1 ----------------------------------------------------------------
TERM_COUNT_SQL = sql.SQL("""
    SELECT COUNT(p_id) AS term_count
    FROM {table}
    WHERE term = %s
    LIMIT 1
""").format(table=APPLICANTS_TABLE)

# --- Q2 ----------------------------------------------------------------
PERCENT_INTERNATIONAL_SQL = sql.SQL("""
    SELECT ROUND(
        (
            (SELECT CAST(COUNT(us_or_international) AS NUMERIC)
                FROM {table} WHERE us_or_international = %s)
            /
            (SELECT CAST(COUNT(us_or_international) AS NUMERIC) FROM {table})
        ) * 100, 2
    )
    LIMIT 1
""").format(table=APPLICANTS_TABLE)

# --- Q3 ----------------------------------------------------------------
AVERAGE_SCORES_SQL = sql.SQL("""
    SELECT
        (SELECT AVG(gpa) FROM {table} WHERE gpa > %s) AS avg_gpa,
        (SELECT AVG(gre) FROM {table} WHERE gre > %s) AS avg_gre,
        (SELECT AVG(gre_v) FROM {table} WHERE gre_v > %s) AS avg_gre_v,
        (SELECT AVG(gre_aw) FROM {table} WHERE gre_aw >= %s) AS avg_gre_aw
    LIMIT 1
""").format(table=APPLICANTS_TABLE)

# --- Q4 ----------------------------------------------------------------
AVERAGE_AMERICAN_GPA_SQL = sql.SQL("""
    SELECT AVG(gpa)
    FROM {table}
    WHERE us_or_international = %s
        AND gpa > %s
        AND term = %s
    LIMIT 1
""").format(table=APPLICANTS_TABLE)

# --- Q5 ----------------------------------------------------------------
PERCENT_ACCEPTED_SQL = sql.SQL("""
    SELECT ROUND(
        (
            (SELECT CAST(COUNT(p_id) AS NUMERIC) FROM {table}
                WHERE status = %s AND term = %s)
            /
            (SELECT CAST(COUNT(p_id) AS NUMERIC) FROM {table} WHERE term = %s)
        ) * 100, 2
    )
    LIMIT 1
""").format(table=APPLICANTS_TABLE)

# --- Q6 ----------------------------------------------------------------
AVERAGE_GPA_FALL_ACCEPTANCE_SQL = sql.SQL("""
    SELECT AVG(gpa)
    FROM {table}
    WHERE term = %s
        AND status = %s
        AND gpa > %s
    LIMIT 1
""").format(table=APPLICANTS_TABLE)

# --- Q7 ----------------------------------------------------------------
JHU_APPLICANTS_SQL = sql.SQL("""
    SELECT COUNT(p_id)
    FROM {table}
    WHERE program LIKE %s
        AND university LIKE %s
        AND degree = %s
    LIMIT 1
""").format(table=APPLICANTS_TABLE)

# --- Q8 ----------------------------------------------------------------
UNI_LIST_ACCEPTANCE_SQL = sql.SQL("""
    SELECT COUNT(p_id)
    FROM {table}
    WHERE extract(YEAR FROM date_added) = %s
        AND degree = %s
        AND program LIKE %s
        AND university LIKE ANY (%s)
        AND status = %s
    LIMIT 1
""").format(table=APPLICANTS_TABLE)

# --- Q9 ----------------------------------------------------------------
LLM_UNI_LIST_ACCEPTANCE_SQL = sql.SQL("""
    SELECT COUNT(p_id)
    FROM {table}
    WHERE extract(YEAR FROM date_added) = %s
        AND degree = %s
        AND llm_generated_program LIKE %s
        AND llm_generated_university LIKE ANY (%s)
        AND status = %s
    LIMIT 1
""").format(table=APPLICANTS_TABLE)

# --- Q10 -----------------------------------------------------------------
BAD_GRE_AW_SCORE_SQL = sql.SQL("""
    SELECT COUNT(p_id)
    FROM {table}
    WHERE gre_aw > %s
    LIMIT 1
""").format(table=APPLICANTS_TABLE)

# --- Q11 -----------------------------------------------------------------
BAD_GRE_SCORES_SQL = sql.SQL("""
    SELECT COUNT(p_id)
    FROM {table}
    WHERE gre > %s
    LIMIT 1
""").format(table=APPLICANTS_TABLE)

# --- New: user-facing, limit-bounded query --------------------------------
RECENT_ENTRIES_SQL = sql.SQL("""
    SELECT p_id, program, university, status, date_added
    FROM {table}
    ORDER BY date_added DESC
    LIMIT %s
""").format(table=APPLICANTS_TABLE)


def get_term_count(conn, term=DEFAULT_TERM):
    """Query the count of applicant entries for a given term.

    :param conn: An active psycopg database connection.
    :type conn: psycopg.Connection
    :param term: The term to filter on, e.g. ``"Fall 2026"``.
    :type term: str
    :return: A single-element tuple containing the count, e.g. ``(142,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        cur.execute(TERM_COUNT_SQL, (term,))
        return cur.fetchone()


def get_international_average(conn, label=DEFAULT_INTERNATIONAL_LABEL):
    """Query the percentage of applicant entries from international students.

    :param conn: An active psycopg database connection.
    :type conn: psycopg.Connection
    :param label: The ``us_or_international`` value to treat as
        "international", e.g. ``"International"``.
    :type label: str
    :return: A single-element tuple containing the percentage, e.g.
        ``(34.57,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        cur.execute(PERCENT_INTERNATIONAL_SQL, (label,))
        return cur.fetchone()


def get_average_scores(conn, sentinel=SENTINEL_MISSING):
    """Query average GPA, GRE, GRE Verbal, and GRE AW scores.

    Sentinel-coded missing values are excluded from each average
    independently, so applicant counts may differ across metrics.

    :param conn: An active psycopg database connection.
    :type conn: psycopg.Connection
    :param sentinel: The sentinel value used to mark a missing score.
    :type sentinel: float
    :return: A four-element tuple ``(avg_gpa, avg_gre, avg_gre_v, avg_gre_aw)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        cur.execute(AVERAGE_SCORES_SQL, (sentinel, sentinel, sentinel, sentinel))
        return cur.fetchone()


def get_american_gpa(conn, label="American", sentinel=SENTINEL_MISSING,
                      term=DEFAULT_TERM):
    """Query the average GPA of American applicants for a given term.

    :param conn: An active psycopg database connection.
    :type conn: psycopg.Connection
    :param label: The ``us_or_international`` value for domestic
        applicants, e.g. ``"American"``.
    :type label: str
    :param sentinel: The sentinel value used to mark a missing GPA.
    :type sentinel: float
    :param term: The term to filter on, e.g. ``"Fall 2026"``.
    :type term: str
    :return: A single-element tuple containing the average GPA.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        cur.execute(AVERAGE_AMERICAN_GPA_SQL, (label, sentinel, term))
        return cur.fetchone()


def get_fall_acceptance_percent(conn, status="Accepted", term=DEFAULT_TERM):
    """Query the percentage of entries for a term that are acceptances.

    :param conn: An active psycopg database connection.
    :type conn: psycopg.Connection
    :param status: The status value counted as an acceptance.
    :type status: str
    :param term: The term to filter on.
    :type term: str
    :return: A single-element tuple containing the acceptance percentage.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        cur.execute(PERCENT_ACCEPTED_SQL, (status, term, term))
        return cur.fetchone()


def get_fall_acceptance_gpa(conn, term=DEFAULT_TERM, status="Accepted",
                             sentinel=SENTINEL_MISSING):
    """Query the average GPA of accepted applicants for a given term.

    :param conn: An active psycopg database connection.
    :type conn: psycopg.Connection
    :param term: The term to filter on.
    :type term: str
    :param status: The status value counted as an acceptance.
    :type status: str
    :param sentinel: The sentinel value used to mark a missing GPA.
    :type sentinel: float
    :return: A single-element tuple containing the average GPA.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        cur.execute(AVERAGE_GPA_FALL_ACCEPTANCE_SQL, (term, status, sentinel))
        return cur.fetchone()


def get_jhu_cs_entries(conn, program_pattern="%Computer Science%",
                        university_pattern="%Johns Hopkins%", degree="Masters"):
    """Query the count of JHU Computer Science Master's entries.

    :param conn: An active psycopg database connection.
    :type conn: psycopg.Connection
    :param program_pattern: ``LIKE`` pattern for the program name.
    :type program_pattern: str
    :param university_pattern: ``LIKE`` pattern for the university name.
    :type university_pattern: str
    :param degree: The degree type to filter on.
    :type degree: str
    :return: A single-element tuple containing the matching count.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        cur.execute(JHU_APPLICANTS_SQL, (program_pattern, university_pattern, degree))
        return cur.fetchone()


def get_uni_acceptances(conn, params=None):
    """Query CS PhD acceptances at a fixed list of universities (raw fields).

    :param conn: An active psycopg database connection.
    :type conn: psycopg.Connection
    :param params: Filter values (year, degree, program pattern,
        university patterns, status). Defaults to
        :class:`AcceptanceQueryParams` with its default values if
        omitted.
    :type params: AcceptanceQueryParams or None
    :return: A single-element tuple containing the matching count.
    :rtype: tuple
    """
    params = params or AcceptanceQueryParams()
    with conn.cursor() as cur:
        cur.execute(UNI_LIST_ACCEPTANCE_SQL,
                    (params.year, params.degree, params.program_pattern,
                     params.universities, params.status))
        return cur.fetchone()


def get_llm_uni_acceptances(conn, params=None):
    """Query CS PhD acceptances at a fixed list of universities (LLM fields).

    Identical in scope to :func:`get_uni_acceptances` but filters on
    ``llm_generated_university`` / ``llm_generated_program`` rather
    than the raw scraped fields.

    :param conn: An active psycopg database connection.
    :type conn: psycopg.Connection
    :param params: Filter values (year, degree, program pattern,
        university patterns, status). Defaults to
        :class:`AcceptanceQueryParams` with its default values if
        omitted.
    :type params: AcceptanceQueryParams or None
    :return: A single-element tuple containing the matching count.
    :rtype: tuple
    """
    params = params or AcceptanceQueryParams()
    with conn.cursor() as cur:
        cur.execute(LLM_UNI_LIST_ACCEPTANCE_SQL,
                    (params.year, params.degree, params.program_pattern,
                     params.universities, params.status))
        return cur.fetchone()


def get_bad_gre_aw_scores(conn, maximum=GRE_AW_MAX):
    """Query the count of GRE AW scores exceeding the maximum attainable.

    :param conn: An active psycopg database connection.
    :type conn: psycopg.Connection
    :param maximum: The maximum valid GRE AW score.
    :type maximum: int or float
    :return: A single-element tuple containing the count of invalid scores.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        cur.execute(BAD_GRE_AW_SCORE_SQL, (maximum,))
        return cur.fetchone()


def get_bad_gre_scores(conn, maximum=GRE_MAX):
    """Query the count of GRE total scores exceeding the maximum attainable.

    :param conn: An active psycopg database connection.
    :type conn: psycopg.Connection
    :param maximum: The maximum valid GRE composite score.
    :type maximum: int or float
    :return: A single-element tuple containing the count of invalid scores.
    :rtype: tuple
    """
    with conn.cursor() as cur:
        cur.execute(BAD_GRE_SCORES_SQL, (maximum,))
        return cur.fetchone()


def get_recent_entries(conn, limit=DEFAULT_LIMIT):
    """Query the most recently added applicant entries, limit-bounded.

    Unlike the aggregate Q1-Q11 queries (which always return exactly
    one row), this is a genuinely user-facing, row-count-driven query:
    ``limit`` is expected to potentially come from request input (e.g.
    ``request.args.get("limit")``) and **must** be passed through
    :func:`clamp_limit` by the caller before reaching this function --
    this function itself does not re-validate it, so callers are
    responsible for clamping untrusted input first.

    :param conn: An active psycopg database connection.
    :type conn: psycopg.Connection
    :param limit: The number of rows to return. Should already be
        clamped via :func:`clamp_limit` by the caller.
    :type limit: int
    :return: Up to ``limit`` rows of
        ``(p_id, program, university, status, date_added)``, most
        recent first.
    :rtype: list[tuple]
    """
    with conn.cursor() as cur:
        cur.execute(RECENT_ENTRIES_SQL, (limit,))
        return cur.fetchall()


def get_stats():
    """Query the database and print descriptive statistics to stdout.

    Opens a single database connection and executes the eleven
    analytical queries (Q1-Q11) by delegating to the corresponding
    accessor functions above, using each function's default filter
    values (the current Fall 2026 application cycle). Results are
    printed to stdout in a numbered format.

    :return: None. All output is written via :func:`print`.
    :rtype: None
    """
    with psycopg.connect(**get_config()) as conn:
        print('1. How many entries do you have in your database who have applied for Fall 2026?')
        print(get_term_count(conn)[0])

        print('2. What percentage of entries are from international students '
              '(not American or Other) (to two decimal places)?')
        print(get_international_average(conn)[0])

        print('3. What is the average GPA, GRE, GRE V, GRE AW of applicants '
              'who provide these metrics?')
        averages = get_average_scores(conn)
        print(f"GPA: {averages[0]}, GRE: {averages[1]}")
        print(f"GRE V: {averages[2]}, GRE AW: {averages[3]}")

        print('4. What is their average GPA of American students in Fall 2026?')
        print(get_american_gpa(conn)[0])

        print('5. What percent of entries for Fall 2026 are Acceptances '
              '(to two decimal places)?')
        print(get_fall_acceptance_percent(conn)[0])

        print('6. What is the average GPA of applicants who applied for '
              'Fall 2026 who are Acceptances?')
        print(get_fall_acceptance_gpa(conn)[0])

        print('7. How many entries are from applicants who applied to JHU '
              'for a masters degrees in Computer Science?')
        print(get_jhu_cs_entries(conn)[0])

        print('8. How many entries from 2026 are acceptances from applicants '
              'who applied to Georgetown University, MIT, Stanford University, '
              'or Carnegie Mellon University for a PhD in Computer Science?')
        print(get_uni_acceptances(conn)[0])

        print('9. Do your numbers for question 8 change if you use LLM '
              'Generated Fields (rather than your downloaded fields)?')
        print(get_llm_uni_acceptances(conn)[0])

        print('10. How many GRE AW scores reported exceeded the maximum '
              'score attainable?')
        print(get_bad_gre_aw_scores(conn)[0])

        print('11. How many GRE scores reported exceeded the maximum score '
              'attainable?')
        print(get_bad_gre_scores(conn)[0])
