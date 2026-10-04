"""
Database persistence layer for cleaned GradCafe application records.

This module defines the ``applicants`` table schema, converts cleaned
application record dictionaries (as produced by a row-cleaning module)
into tuples suitable for bulk insertion, and performs the actual
insert against a PostgreSQL database via :mod:`psycopg`.

The intended pipeline is: scrape → clean (produces a list of record
dictionaries with string-typed fields) → :func:`insert_entries` (this
module), which handles numeric/date type coercion and persistence.

**Module contents:**

+----------------------------+----------------------------------------------+
| Name                       | Description                                  |
+==============================+============================================+
| :data:`CREATE_TABLE_SQL`   | DDL for the ``applicants`` table             |
+----------------------------+----------------------------------------------+
| :data:`INSERT_SQL`         | Parameterised bulk-insert statement          |
+----------------------------+----------------------------------------------+
| :func:`_create_tuples_list`| Convert record dicts to DB-ready tuples      |
+----------------------------+----------------------------------------------+
| :func:`insert_entries`     | Public entry point: convert and bulk-insert  |
+----------------------------+----------------------------------------------+

**Dependencies:**

* :mod:`datetime` -- standard library, used to parse ``date_added``
  strings into :class:`datetime.date` objects.
* :mod:`psycopg` -- third-party (psycopg 3), used to open a database
  connection, execute DDL, and perform the bulk insert.
* :mod:`src.config` -- local module, supplies ``config``, a mapping of
  connection parameters passed to :func:`psycopg.connect` via
  ``**config``.

**Database schema (``applicants`` table):**

Defined by :data:`CREATE_TABLE_SQL`, with ``p_id`` as the primary key.
Columns: ``p_id`` (integer), ``program``, ``university``, ``comments``,
``date_added`` (date), ``url``, ``status``, ``term``,
``us_or_international``, ``gpa`` (float), ``gre`` (float), ``gre_v``
(float), ``gre_aw`` (float), ``degree``, ``llm_generated_program``,
``llm_generated_university``. Note the naming mismatch between this
schema's snake_case columns (e.g. ``gre_v``, ``us_or_international``)
and the corresponding source dictionary keys consumed elsewhere in the
pipeline (e.g. ``grev``, ``US/International``) -- the field mapping is
handled explicitly within :func:`_create_tuples_list` and
:data:`INSERT_SQL`.

.. note::
    :data:`CREATE_TABLE_SQL` is defined in this module but is not
    executed by any function within it; callers must run it
    separately (e.g. once, during application setup) to ensure the
    ``applicants`` table exists before :func:`insert_entries` is
    called.

.. warning::
    Missing numeric fields (``gpa``, ``gre``, ``grev``, ``greaw``) are
    expected as the string ``"None"`` on input and are converted to
    the float sentinel ``-1.0`` by :func:`_create_tuples_list`, rather
    than to SQL ``NULL``. This convention must stay consistent with
    any downstream queries (e.g. statistics/reporting code) that
    filter on these columns, or aggregates will be skewed by the
    sentinel values.

.. warning::
    :func:`insert_entries` calls ``conn.close()`` in a ``finally``
    block following a ``with psycopg.connect(**config) as conn:``
    statement. If :func:`psycopg.connect` itself raises (e.g. due to
    invalid credentials or an unreachable host), ``conn`` is never
    assigned, and the ``finally`` block's ``conn.close()`` will raise
    :exc:`UnboundLocalError`, masking the original connection error.
    Additionally, the ``with`` block already closes the connection on
    exit, making the explicit ``conn.close()`` redundant in the
    success path.

**Typical usage:**

.. code-block:: python

    from src import clean, persist

    records = clean.clean_data(table_rows, last_id_fetched=0)
    if records:
        persist.insert_entries(records)

.. seealso::
    The row-cleaning module (e.g. :mod:`src.clean`) that produces the
    ``scraped_data`` record dictionaries consumed by
    :func:`insert_entries`.

    The statistics/reporting module that queries the ``applicants``
    table populated by this module, in particular regarding the
    ``-1.0`` sentinel convention for missing scores.
"""
import os
import json
from datetime import datetime
import psycopg
from psycopg.rows import dict_row
from psycopg import errors as pg_errors
from psycopg import sql
def _load_data():
    with open("applicant_data.json", 'r', encoding="utf-8") as f:
        return json.load(f)

def _create_tuples_list(scraped_data):
    """
    Convert a list of application record dictionaries into a list of
    tuples suitable for bulk database insertion.

    Iterates over ``scraped_data``, coercing numeric fields from their
    string representations to ``float``, substituting ``-1.0`` for any
    missing values (stored as the string ``"None"``), and parsing
    ``date_added`` from a human-readable string into a :class:`datetime.date`
    object. Each record is then packed into a tuple whose column order
    matches the target database schema.

    :param scraped_data: A list of application record dictionaries, each
                        produced by :func:`clean_data`. Records are
                        mutated in place during type conversion.
    :type scraped_data: list[dict]
    :returns: A list of 16-element tuples ready for bulk database
              insertion, one tuple per input record.
    :rtype: list[tuple]

    .. note::
        Missing numeric scores are sentinel-coded as ``-1.0`` rather
        than ``None`` to simplify downstream SQL filtering and avoid
        ``NULL`` handling. Ensure the target database schema and any
        queries account for this convention.
    """
    insert_data = []
    # Create a list of tuples from the dictionaries to bulk insert
    for data in scraped_data:
        # Convert datatypes first, missing value assigned as -1 for easier filtering
        if data["gpa"] == "None":
            data["gpa"] = -1.0
        else:
            data["gpa"] = float(data["gpa"])

        if data["gre"] == "None":
            data["gre"] = -1.0
        else:
            data["gre"] = float(data["gre"])

        if data["grev"] == "None":
            data["grev"] = -1.0
        else:
            data["grev"] = float(data["grev"])

        if data["greaw"] == "None":
            data["greaw"] = -1.0
        else:
            data["greaw"] = float(data["greaw"])

        # Create the tuple for iteration
        insert_data.append((data["id"],
                        data["program"],
                        data["degree"],
                        data["university"],
                        data["comments"],
                        datetime.strptime(data["date_added"],"%b %d, %Y").date(),
                        data["url"],
                        data["status"],
                        data["term"],
                        data["US/International"],
                        data["gpa"],
                        data["gre"],
                        data["grev"],
                        data["greaw"],
                        data["llm-generated-program"],
                        data["llm-generated-university"]))
    return insert_data




INSERT_SQL = """
    INSERT INTO applicants
    (p_id, program, degree, university, comments, date_added, url, status,
    term, us_or_international, gpa, gre, gre_v, gre_aw, llm_generated_program,
    llm_generated_university)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (p_id) DO NOTHING;
"""

UPDATE_WATERMARK_SQL = """
    UPDATE ingestion_watermarks SET last_seen = %s, updated_at = NOW() WHERE source = 'WEB';
"""

INSERT_WATERMARK_SQL = """
    INSERT INTO ingestion_watermarks (source, last_seen, updated_at)
    VALUES ('WEB', %s, NOW());
"""

COMPILED_ANALYTICS = """
CREATE MATERIALIZED VIEW compiled_analytics AS
SELECT
(SELECT COUNT(p_id) 
FROM applicants
WHERE term = 'Fall 2026'
LIMIT 1) AS term_count,
(SELECT
ROUND(((
SELECT CAST(COUNT(us_or_international) AS NUMERIC) FROM applicants WHERE us_or_international = 'International'
)
/
(
SELECT CAST(COUNT(us_or_international) AS NUMERIC) FROM applicants
)
) * 100, 2)LIMIT 1) AS percent_international,

(SELECT AVG(gpa) FROM applicants WHERE gpa > 0 LIMIT 1) AS average_gpa,
(SELECT AVG(gre) FROM applicants WHERE gre > 0 LIMIT 1) AS average_gre,
(SELECT AVG(gre_v) FROM applicants WHERE gre_v > 0 LIMIT 1) AS average_grev,
(SELECT AVG(gre_aw) FROM applicants WHERE gre_aw >= 0 LIMIT 1) AS average_gre_aw,

(SELECT AVG(gpa)
FROM applicants
WHERE us_or_international = 'American'
AND gpa > 0
AND term = 'Fall 2026'
LIMIT 1) AS average_american_gpa,

(SELECT
ROUND(((
SELECT CAST(COUNT(p_id) AS NUMERIC) FROM applicants WHERE status = 'Accepted' AND term = 'Fall 2026'
)
/
(
SELECT CAST(COUNT(p_id) AS NUMERIC) FROM applicants WHERE term = 'Fall 2026'
)
) * 100, 2) LIMIT 1) AS percent_accepted,

(SELECT AVG(gpa)
FROM applicants
WHERE term = 'Fall 2026'
AND status = 'Accepted'
AND gpa > 0
LIMIT 1) AS average_gpa_fall_acceptance,

(SELECT count(p_id)
FROM applicants
WHERE program LIKE '%Computer Science%'
AND university LIKE '%Johns Hopkins%'
AND degree = 'Masters'
LIMIT 1) AS jhu_applicants,

(SELECT COUNT(p_id)
FROM applicants
WHERE extract(YEAR FROM date_added) = 2026
AND degree = 'PhD'
AND program LIKE '%Computer Science%'
AND university LIKE ANY (ARRAY['%Georgetown University%','%Massachusetts Institute of Technology%','%MIT%','%Stanford University%','%Carnegie Mellon%'])
AND status = 'Accepted'
LIMIT 1) AS uni_list_acceptance,

(SELECT COUNT(p_id)
FROM applicants
WHERE extract(YEAR FROM date_added) = 2026
AND degree = 'PhD'
AND llm_generated_program LIKE '%Computer Science%'
AND llm_generated_university LIKE ANY (ARRAY['%Georgetown University%','%Massachusetts Institute of Technology%','%MIT%','%Stanford University%','%Carnegie Mellon%'])
AND status = 'Accepted'
LIMIT 1) AS llm_uni_list_acceptance,

(SELECT COUNT(p_id)
FROM applicants
WHERE gre_aw > 6
LIMIT 1) AS bad_gre_aw_scores,

(SELECT COUNT(p_id)
FROM applicants
WHERE gre > 340
LIMIT 1) AS bad_gre_scores;
"""
DATA_PRESENT_SQL = "SELECT COUNT(p_id) AS count FROM applicants LIMIT 1;"

GET_MAX_ID_SQL = "SELECT MAX(p_id) AS max_id FROM applicants;"

CHECK_WATERMARK_SQL="SELECT COUNT(source) AS count FROM ingestion_watermarks WHERE source = 'WEB';"

MATERIALIZED_VIEW_SELECT_SQL = "SELECT * FROM compiled_analytics"

USER_ADD_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = {rolname}) THEN
        CREATE USER {username}
            WITH PASSWORD {password}
            NOSUPERUSER     -- cannot perform superuser operations
            NOCREATEDB      -- cannot create databases
            NOCREATEROLE    -- cannot create roles or users
            NOINHERIT       -- does not inherit privileges of roles it is a member of
            LOGIN;          -- can log in
    END IF;
END $$;
"""

CREATE_REFRESH_SQL = """
-- Create a function that refreshes the view
CREATE OR REPLACE FUNCTION public.refresh_compiled_analytics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.compiled_analytics;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
CREATE UNIQUE INDEX IF NOT EXISTS idx_compiled_analytics
    ON compiled_analytics(term_count);
-- Grant user the ability to call it
"""

USER_GRANT_SQL = """
-- Grant accesses
GRANT SELECT, INSERT ON public.applicants TO {user1};
GRANT SELECT, INSERT, UPDATE ON public.ingestion_watermarks TO {user2};
GRANT SELECT ON public.compiled_analytics TO {user3};
GRANT EXECUTE ON FUNCTION public.refresh_compiled_analytics() TO {user4};
"""

MV_REFRESH_SQL = "REFRESH MATERIALIZED VIEW compiled_analytics;"

def insert_entries(scraped_data):
    """
    Bulk insert scraped application records into the ``applicants``
    database table.

    Converts ``scraped_data`` into a list of tuples via
    :func:`_create_tuples_list` and executes a parameterised bulk insert
    against the ``applicants`` table using :func:`psycopg.connect` and
    :meth:`cursor.executemany`. The transaction is committed on success
    and the connection is always closed in the ``finally`` block.

    :param scraped_data: A list of application record dictionaries as
                        returned by :func:`clean_data`. Passed directly
                        to :func:`_create_tuples_list`, which mutates
                        records in place during type coercion.
    :type scraped_data: list[dict]
    :returns: None.
    :rtype: None
    """
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                cur.executemany(INSERT_SQL, _create_tuples_list(scraped_data))
                conn.commit()
    finally:
        conn.close()

if __name__=='__main__':
    try:
        with psycopg.connect(os.getenv("DATABASE_URL"), row_factory=dict_row) as db_conn:
            with db_conn.cursor() as db_cur:
                # Uncomment to restore the database to neutral state
                # truncate_database_sql = "TRUNCATE applicants"
                # db_cur.execute(truncate_database_sql)

                # Check if data is already imported and persisted, if not, import it

                db_cur.execute(DATA_PRESENT_SQL)

                if db_cur.fetchone()['count'] == 0:
                    db_cur.executemany(INSERT_SQL, _create_tuples_list(_load_data()))
                    db_conn.commit()
                    print("Applicant Data Import Completed")
                else:
                    print("Applicant data found, skipping import")

                # Grab max ID and update the watermark
                db_cur.execute(GET_MAX_ID_SQL)
                max_seen_id = db_cur.fetchone()["max_id"]
                print(f"Max ID fetched: {max_seen_id}")
                # Check for watermark entry, UPDATE is exists, INSERT if no entry

                db_cur.execute(CHECK_WATERMARK_SQL)
                watermark = db_cur.fetchone()["count"]
                print("Searching For Watermark")
                if watermark == 1:
                    print(f"Watermark Found ({watermark}), Updating...")
                    db_cur.execute(UPDATE_WATERMARK_SQL, (max_seen_id,))
                    db_conn.commit()
                    print("Watermark Updated")
                else:
                    print("Watermark Not Found, Creating...")
                    db_cur.execute(INSERT_WATERMARK_SQL, (max_seen_id,))
                    db_conn.commit()
                    print("New Watermark Added")

                # Create the initial materialized view
                # Check if materialized view was created
                print("Searching For Materialized View")
                try:
                    db_cur.execute(MATERIALIZED_VIEW_SELECT_SQL)
                    table = db_cur.fetchone()
                    print("Materialized View Found, Updating...")
                    # Table exists, refresh view
                    db_cur.execute(MV_REFRESH_SQL)
                    print("Materialized View Updated")
                except pg_errors.UndefinedTable:
                    # MV doesn't exist, rollback error, create the view
                    db_conn.rollback()
                    print("Materialized View not found, Creating...")
                    db_cur.execute(COMPILED_ANALYTICS)
                    print("Materialized View Created")
                db_conn.commit()

                # Check for regular user and insert if not present
                user_account = os.getenv("DB_USER")
                user_pass = os.getenv("USER_PASS")
                fill_with = (user_account, user_account, user_pass)
                db_cur.execute(sql.SQL(USER_ADD_SQL).format(
        rolname=sql.Literal(user_account),
        username=sql.Identifier(user_account),
        password=sql.Literal(user_pass),))
                db_cur.execute(CREATE_REFRESH_SQL)
                db_cur.execute(sql.SQL(USER_GRANT_SQL).format(
                    user1=sql.Identifier(user_account),
                    user2=sql.Identifier(user_account),
                    user3=sql.Identifier(user_account),
                    user4=sql.Identifier(user_account),))
                db_conn.commit()
                print("Reduced Privilege User Added")

    except (pg_errors.ConnectionFailure,
            pg_errors.ConnectionTimeout,
            pg_errors.DatabaseError) as e:
        print(f"Error: {e}")
    finally:
        db_conn.close()
