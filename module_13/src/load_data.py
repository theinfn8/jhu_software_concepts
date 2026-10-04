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
| :data:`INSERT_SQL`         | Parameterised bulk-insert statement (scraper |
|                             | pipeline)                                    |
+----------------------------+----------------------------------------------+
| :data:`INSERT_JSON_SQL`    | Same insert, with ``ON CONFLICT (p_id) DO    |
|                             | NOTHING`` for re-runnable JSON bulk loads    |
+----------------------------+----------------------------------------------+
| :func:`_create_tuples_list`| Convert scraper-pipeline record dicts to     |
|                             | DB-ready tuples                              |
+----------------------------+----------------------------------------------+
| :func:`insert_entries`     | Public entry point: convert and bulk-insert  |
|                             | scraper-pipeline records                     |
+----------------------------+----------------------------------------------+
| :func:`_map_json_record`   | Convert one ``cleaned_gradcafe.json`` record  |
|                             | dict to a DB-ready tuple                     |
+----------------------------+----------------------------------------------+
| :func:`load_json_into_database` | Public entry point: create the table if |
|                             | missing, then bulk-load a cleaned JSON export|
+----------------------------+----------------------------------------------+

**Dependencies:**

* :mod:`datetime` -- standard library, used to parse ``date_added``
  strings into :class:`datetime.date` objects (both pipelines, though
  with different source string formats -- see :func:`_create_tuples_list`
  vs. :func:`_map_json_record`).
* :mod:`json` -- standard library, used by :func:`load_json_into_database`
  to parse the cleaned JSON export.
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
and the source field names consumed by each loading path -- there are
two independent mappings onto this same schema, handled explicitly by
:func:`_create_tuples_list` (scraper pipeline field names, e.g.
``grev``, ``US/International``) and :func:`_map_json_record` (cleaned
JSON export field names, e.g. ``"GRE V"``, ``US/International``).

.. note::
    :data:`CREATE_TABLE_SQL` is idempotent (``CREATE TABLE IF NOT
    EXISTS``). :func:`load_json_into_database` executes it directly, so
    calling that function is sufficient to ensure the ``applicants``
    table exists before it is populated. :func:`insert_entries`, by
    contrast, does *not* execute it -- callers using the scraper-based
    ``insert_entries`` path must still ensure the table exists first
    (e.g. by having already called :func:`load_json_into_database` at
    least once, or by executing :data:`CREATE_TABLE_SQL` separately).

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

    from src import clean, load_data

    # One-time (or occasional) bulk load from a cleaned JSON export --
    # also ensures the applicants table exists.
    load_data.load_json_into_database("data/cleaned_gradcafe.json")

    # Incremental updates from a fresh scrape, via the existing
    # scraper -> clean -> insert pipeline. Assumes the table already
    # exists (e.g. from the bulk load above).
    records = clean.clean_data(table_rows, last_id_fetched=0)
    if records:
        load_data.insert_entries(records)

.. seealso::
    The row-cleaning module (e.g. :mod:`src.clean`) that produces the
    ``scraped_data`` record dictionaries consumed by
    :func:`insert_entries`.

    The statistics/reporting module that queries the ``applicants``
    table populated by this module, in particular regarding the
    ``-1.0`` sentinel convention for missing scores.
"""

from datetime import datetime
import json
import psycopg
from src.config import get_config

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

    **Type conversions applied:**

    +---------------+----------------+-----------------------------+
    | Field         | Missing value  | Conversion                  |
    +===============+================+=============================+
    | ``gpa``       | ``-1.0``       | ``float``                   |
    +---------------+----------------+-----------------------------+
    | ``gre``       | ``-1.0``       | ``float``                   |
    +---------------+----------------+-----------------------------+
    | ``grev``      | ``-1.0``       | ``float``                   |
    +---------------+----------------+-----------------------------+
    | ``greaw``     | ``-1.0``       | ``float``                   |
    +---------------+----------------+-----------------------------+
    | ``date_added``| N/A            | ``datetime.date`` via       |
    |               |                | ``"%b %d, %Y"``             |
    +---------------+----------------+-----------------------------+

    **Output tuple column order:**

    +-----+------------------------------+
    | Pos | Field                        |
    +=====+==============================+
    | 0   | ``id``                       |
    +-----+------------------------------+
    | 1   | ``program``                  |
    +-----+------------------------------+
    | 2   | ``university``               |
    +-----+------------------------------+
    | 3   | ``comments``                 |
    +-----+------------------------------+
    | 4   | ``date_added``               |
    +-----+------------------------------+
    | 5   | ``url``                      |
    +-----+------------------------------+
    | 6   | ``status``                   |
    +-----+------------------------------+
    | 7   | ``term``                     |
    +-----+------------------------------+
    | 8   | ``US/International``         |
    +-----+------------------------------+
    | 9   | ``gpa``                      |
    +-----+------------------------------+
    | 10  | ``gre``                      |
    +-----+------------------------------+
    | 11  | ``grev``                     |
    +-----+------------------------------+
    | 12  | ``greaw``                    |
    +-----+------------------------------+
    | 13  | ``degree``                   |
    +-----+------------------------------+
    | 14  | ``llm-generated-program``    |
    +-----+------------------------------+
    | 15  | ``llm-generated-university`` |
    +-----+------------------------------+

    :param scraped_data: A list of application record dictionaries, each
                        produced by :func:`clean_data`. Records are
                        mutated in place during type conversion.
    :type scraped_data: list[dict]
    :returns: A list of 16-element tuples ready for bulk database
              insertion, one tuple per input record.
    :rtype: list[tuple]

    :raises ValueError: If ``date_added`` does not match the expected
                        format ``"%b %d, %Y"`` (e.g. ``"Jan 05, 2025"``),
                        or if a non-``"None"`` GPA or GRE value cannot
                        be cast to ``float``.
    :raises KeyError: If a required field is absent from a record
                      dictionary.

    .. note::
        ``scraped_data`` is mutated in place during numeric type
        coercion. If the original dictionaries must be preserved,
        pass a deep copy of the list.

    .. note::
        Missing numeric scores are sentinel-coded as ``-1.0`` rather
        than ``None`` to simplify downstream SQL filtering and avoid
        ``NULL`` handling. Ensure the target database schema and any
        queries account for this convention.
    """
    insert_data = []
    # Create a list of tuples from the dictionaries to bulk insert
    for datum in scraped_data:
        # Convert datatypes first, missing value assigned as -1 for easier filtering
        if datum["gpa"] == "None":
            datum["gpa"] = -1.0
        else:
            datum["gpa"] = float(datum["gpa"])

        if datum["gre"] == "None":
            datum["gre"] = -1.0
        else:
            datum["gre"] = float(datum["gre"])

        if datum["grev"] == "None":
            datum["grev"] = -1.0
        else:
            datum["grev"] = float(datum["grev"])

        if datum["greaw"] == "None":
            datum["greaw"] = -1.0
        else:
            datum["greaw"] = float(datum["greaw"])

        # Create the tuple for iteration
        insert_data.append((datum["id"],
                        datum["program"],
                        datum["university"],
                        datum["comments"],
                        datetime.strptime(datum["date_added"],"%b %d, %Y").date(),
                        datum["url"],
                        datum["status"],
                        datum["term"],
                        datum["US/International"],
                        datum["gpa"],
                        datum["gre"],
                        datum["grev"],
                        datum["greaw"],
                        datum["degree"],
                        datum["llm-generated-program"],
                        datum["llm-generated-university"]
                        ))
    return insert_data

CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS applicants (
    p_id integer PRIMARY KEY,
    program text,
    university text,
    comments text,
    date_added date,
    url text,
    status text,
    term text,
    us_or_international text,
    gpa float,
    gre float,
    gre_v float,
    gre_aw float,
    degree text,
    llm_generated_program text,
    llm_generated_university text
);
"""

INSERT_SQL = """
    INSERT INTO applicants (p_id, program, university, comments, date_added, url, status,
    term, us_or_international, gpa, gre, gre_v, gre_aw, degree, llm_generated_program, llm_generated_university)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

# Same column list as INSERT_SQL, but with an ON CONFLICT clause so bulk
# JSON loads (see load_json_into_database) are safely re-runnable without
# raising a duplicate-primary-key error on p_id.
INSERT_JSON_SQL = INSERT_SQL.strip() + " ON CONFLICT (p_id) DO NOTHING"


def _map_json_record(record):
    """
    Convert one record dict from ``cleaned_gradcafe.json`` into a
    DB-ready tuple matching the ``applicants`` table's column order.

    This is a **separate** conversion path from
    :func:`_create_tuples_list`, which is specifically scoped to the
    field names and value conventions produced by the live scrape ->
    :func:`src.clean.clean_data` pipeline (e.g. ``id``, ``grev``,
    ``US/International``, dates as ``"%b %d, %Y"`` strings, missing
    numbers as the literal string ``"None"``). The pre-cleaned JSON
    dataset has a different schema entirely -- different field names
    (``Program``/``University``/``Degree``/``outcome`` instead of
    ``program``/``university``/``degree``/``status``, ``"GRE V"``/
    ``"GRE AW"`` instead of ``grev``/``greaw``), different missing-value
    representation (JSON ``null`` instead of the string ``"None"``),
    and a different date format (ISO 8601 instead of ``"%b %d, %Y"``).
    Rather than force this through the scraper-specific conversion (and
    have to re-stringify values just so they can be re-parsed), this
    function maps directly from the JSON schema to the final tuple.

    **Field mapping (JSON key -> tuple position / DB column):**

    +-------------------------------+-------------------------------+
    | JSON key                      | DB column                     |
    +===============================+=================================+
    | ``id``                        | ``p_id``                      |
    +-------------------------------+-------------------------------+
    | ``Program``                   | ``program``                   |
    +-------------------------------+-------------------------------+
    | ``University``                | ``university``                |
    +-------------------------------+-------------------------------+
    | ``comments``                  | ``comments``                  |
    +-------------------------------+-------------------------------+
    | ``date_added`` (ISO 8601)     | ``date_added``                |
    +-------------------------------+-------------------------------+
    | ``url``                       | ``url``                       |
    +-------------------------------+-------------------------------+
    | ``outcome``                   | ``status``                    |
    +-------------------------------+-------------------------------+
    | ``term``                      | ``term``                      |
    +-------------------------------+-------------------------------+
    | ``US/International``          | ``us_or_international``       |
    +-------------------------------+-------------------------------+
    | ``GPA``                       | ``gpa``                       |
    +-------------------------------+-------------------------------+
    | ``GRE``                       | ``gre``                       |
    +-------------------------------+-------------------------------+
    | ``GRE V``                     | ``gre_v``                     |
    +-------------------------------+-------------------------------+
    | ``GRE AW``                    | ``gre_aw``                    |
    +-------------------------------+-------------------------------+
    | ``Degree``                    | ``degree``                    |
    +-------------------------------+-------------------------------+
    | ``llm-generated-program``     | ``llm_generated_program``     |
    +-------------------------------+-------------------------------+
    | ``llm-generated-university``  | ``llm_generated_university``  |
    +-------------------------------+-------------------------------+

    :param record: A single record dict as loaded from
        ``cleaned_gradcafe.json``.
    :type record: dict
    :returns: A 16-element tuple in the same column order as
        :data:`INSERT_SQL` / :data:`INSERT_JSON_SQL`.
    :rtype: tuple

    .. note::
        Missing numeric scores (``GPA``, ``GRE``, ``GRE V``, ``GRE AW``)
        arrive as JSON ``null`` (Python ``None``) rather than the
        string ``"None"`` used by the scraper pipeline, but are
        converted to the same ``-1.0`` sentinel used throughout this
        module and by the statistics/reporting queries, so both
        loading paths remain consistent for downstream consumers.
    """
    def _numeric_or_sentinel(value):
        return -1.0 if value is None else float(value)

    return (
        record["id"],
        record.get("Program") or "Unknown",
        record.get("University") or "Unknown",
        record.get("comments") or "None",
        datetime.fromisoformat(record["date_added"]).date(),
        record["url"],
        record["outcome"],
        record["term"],
        record["US/International"],
        _numeric_or_sentinel(record.get("GPA")),
        _numeric_or_sentinel(record.get("GRE")),
        _numeric_or_sentinel(record.get("GRE V")),
        _numeric_or_sentinel(record.get("GRE AW")),
        record.get("Degree") or "Unknown",
        record.get("llm-generated-program") or "Unknown",
        record.get("llm-generated-university") or "Unknown",
    )


def load_json_into_database(json_path):
    """
    Ensure the ``applicants`` table exists, then bulk-load a cleaned
    GradCafe JSON export (e.g. ``cleaned_gradcafe.json``) into it.

    Unlike :func:`insert_entries` (which assumes its input already
    matches the live scraper's field names/conventions),
    this function is meant for a one-time or occasional bulk load of a
    pre-cleaned dataset with its own schema -- see
    :func:`_map_json_record` for the exact field mapping applied.

    Steps performed, in a single connection:

    1. Executes :data:`CREATE_TABLE_SQL` (``CREATE TABLE IF NOT
       EXISTS``), so this is safe to call whether or not the table
       already exists.
    2. Reads and parses ``json_path`` as a JSON array of record dicts.
    3. Converts every record via :func:`_map_json_record`.
    4. Bulk-inserts all records via :data:`INSERT_JSON_SQL`, which
       includes ``ON CONFLICT (p_id) DO NOTHING`` -- so re-running this
       function against the same file (e.g. after a partial failure,
       or during iterative testing) does not raise a duplicate-primary-
       key error; rows already present by ``p_id`` are simply skipped,
       not updated.
    5. Commits the transaction.

    :param json_path: Path to a JSON file containing a top-level array
        of applicant record dicts in the ``cleaned_gradcafe.json``
        schema (see :func:`_map_json_record`).
    :type json_path: str
    :returns: The number of records read from the file (not
        necessarily the number of *new* rows inserted, since existing
        ``p_id`` values are silently skipped rather than counted).
    :rtype: int

    :raises FileNotFoundError: If no file exists at ``json_path``.
    :raises json.JSONDecodeError: If ``json_path`` does not contain
        valid JSON.
    :raises KeyError: If a record is missing one of the required keys
        (``id``, ``date_added``, ``url``, ``outcome``, ``term``, or
        ``US/International``) that :func:`_map_json_record` does not
        already default -- unlike ``Program``/``University``/``Degree``/
        the ``llm-generated-*`` fields, these do not fall back to
        ``"Unknown"``, since a missing id/date/url/outcome/term/
        citizenship indicates a genuinely malformed source record
        rather than an applicant simply leaving a field blank.
    :raises ValueError: If ``date_added`` is not valid ISO 8601, or a
        numeric field cannot be coerced to ``float``.
    :raises psycopg.OperationalError: If the database connection
        cannot be established.
    :raises psycopg.DatabaseError: If the ``CREATE TABLE`` statement or
        the bulk insert fails at the database level.

    .. note::
        This function does not delete or truncate any existing data;
        it only creates the table if missing and adds new rows. To
        reload from scratch, drop or truncate the ``applicants`` table
        first.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    tuples = [_map_json_record(record) for record in records]

    with psycopg.connect(**get_config()) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
            cur.executemany(INSERT_JSON_SQL, tuples)
        conn.commit()

    return len(records)

def insert_entries(scraped_data):
    """
    Bulk insert scraped application records into the ``applicants``
    database table.

    Converts ``scraped_data`` into a list of tuples via
    :func:`_create_tuples_list` and executes a parameterised bulk insert
    against the ``applicants`` table using :func:`psycopg.connect` and
    :meth:`cursor.executemany`. The transaction is committed on success
    and the connection is always closed in the ``finally`` block.

    The target table schema and column mapping are as follows:

    +------+------------------------------+------------------------------+
    | Pos  | DB Column                    | Source Field                 |
    +======+==============================+==============================+
    | 1    | ``p_id``                     | ``id``                       |
    +------+------------------------------+------------------------------+
    | 2    | ``program``                  | ``program``                  |
    +------+------------------------------+------------------------------+
    | 3    | ``university``               | ``university``               |
    +------+------------------------------+------------------------------+
    | 4    | ``comments``                 | ``comments``                 |
    +------+------------------------------+------------------------------+
    | 5    | ``date_added``               | ``date_added``               |
    +------+------------------------------+------------------------------+
    | 6    | ``url``                      | ``url``                      |
    +------+------------------------------+------------------------------+
    | 7    | ``status``                   | ``status``                   |
    +------+------------------------------+------------------------------+
    | 8    | ``term``                     | ``term``                     |
    +------+------------------------------+------------------------------+
    | 9    | ``us_or_international``      | ``US/International``         |
    +------+------------------------------+------------------------------+
    | 10   | ``gpa``                      | ``gpa``                      |
    +------+------------------------------+------------------------------+
    | 11   | ``gre``                      | ``gre``                      |
    +------+------------------------------+------------------------------+
    | 12   | ``gre_v``                    | ``grev``                     |
    +------+------------------------------+------------------------------+
    | 13   | ``gre_aw``                   | ``greaw``                    |
    +------+------------------------------+------------------------------+
    | 14   | ``degree``                   | ``degree``                   |
    +------+------------------------------+------------------------------+
    | 15   | ``llm_generated_program``    | ``llm-generated-program``    |
    +------+------------------------------+------------------------------+
    | 16   | ``llm_generated_university`` | ``llm-generated-university`` |
    +------+------------------------------+------------------------------+

    :param scraped_data: A list of application record dictionaries as
                        returned by :func:`clean_data`. Passed directly
                        to :func:`_create_tuples_list`, which mutates
                        records in place during type coercion.
    :type scraped_data: list[dict]
    :returns: None.
    :rtype: None

    :raises psycopg.OperationalError: If the database connection cannot
                                      be established, e.g. due to invalid
                                      credentials or an unreachable host
                                      in the module-level ``config`` dict.
    :raises psycopg.IntegrityError: If any record violates a database
                                    constraint, such as a duplicate
                                    ``p_id`` or a ``NOT NULL`` violation.
                                    The transaction is not committed in
                                    this case.
    :raises psycopg.DatabaseError: For any other database-level error
                                   encountered during ``executemany``.
    :raises ValueError: If :func:`_create_tuples_list` fails to coerce a
                        field value, e.g. a malformed ``date_added``
                        string or a non-numeric GPA.

    .. note::
        Database connection parameters are read from the module-level
        ``config`` dictionary, which is unpacked as keyword arguments
        into :func:`psycopg.connect`. Ensure ``config`` contains valid
        ``host``, ``dbname``, ``user``, and ``password`` keys before
        calling this function.

    .. warning::
        If a :exc:`psycopg.IntegrityError` or other database exception
        is raised during ``executemany``, the transaction is rolled back
        but the exception propagates to the caller uncaught. Consider
        wrapping calls to this function in a ``try/except`` block to
        handle partial failure gracefully.
    """
    try:
        with psycopg.connect(**get_config()) as conn:
            with conn.cursor() as cur:
                cur.executemany(INSERT_SQL, _create_tuples_list(scraped_data))
                conn.commit()
    finally:
        conn.close()
