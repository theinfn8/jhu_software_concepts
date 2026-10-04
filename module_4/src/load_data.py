import json
import psycopg
from src.config import config
from datetime import datetime

def _createTuplesList(scrapedData):
    """
    Convert a list of application record dictionaries into a list of
    tuples suitable for bulk database insertion.

    Iterates over ``scrapedData``, coercing numeric fields from their
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

    +-----+-------------------------+
    | Pos | Field                   |
    +=====+=========================+
    | 0   | ``id``                  |
    +-----+-------------------------+
    | 1   | ``program``             |
    +-----+-------------------------+
    | 2   | ``university``          |
    +-----+-------------------------+
    | 3   | ``comments``            |
    +-----+-------------------------+
    | 4   | ``date_added``          |
    +-----+-------------------------+
    | 5   | ``url``                 |
    +-----+-------------------------+
    | 6   | ``status``              |
    +-----+-------------------------+
    | 7   | ``term``                |
    +-----+-------------------------+
    | 8   | ``US/International``    |
    +-----+-------------------------+
    | 9   | ``gpa``                 |
    +-----+-------------------------+
    | 10  | ``gre``                 |
    +-----+-------------------------+
    | 11  | ``grev``                |
    +-----+-------------------------+
    | 12  | ``greaw``               |
    +-----+-------------------------+
    | 13  | ``degree``              |
    +-----+-------------------------+
    | 14  | ``llm-generated-program``    |
    +-----+-------------------------+
    | 15  | ``llm-generated-university`` |
    +-----+-------------------------+

    :param scrapedData: A list of application record dictionaries, each
                        produced by :func:`clean_data`. Records are
                        mutated in place during type conversion.
    :type scrapedData: list[dict]
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
        ``scrapedData`` is mutated in place during numeric type
        coercion. If the original dictionaries must be preserved,
        pass a deep copy of the list.

    .. note::
        Missing numeric scores are sentinel-coded as ``-1.0`` rather
        than ``None`` to simplify downstream SQL filtering and avoid
        ``NULL`` handling. Ensure the target database schema and any
        queries account for this convention.
    """
    insertData = list()
    # Create a list of tuples from the dictionaries to bulk insert
    for datum in scrapedData:
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
        insertData.append((datum["id"],
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
    return insertData

createTableSQL = """
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

insertSQL = """
    INSERT INTO applicants (p_id, program, university, comments, date_added, url, status,
    term, us_or_international, gpa, gre, gre_v, gre_aw, degree, llm_generated_program, llm_generated_university)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

def insertEntries(scrapedData):
    """
    Bulk insert scraped application records into the ``applicants``
    database table.

    Converts ``scrapedData`` into a list of tuples via
    :func:`_createTuplesList` and executes a parameterised bulk insert
    against the ``applicants`` table using :func:`psycopg.connect` and
    :meth:`cursor.executemany`. The transaction is committed on success
    and the connection is always closed in the ``finally`` block.

    The target table schema and column mapping are as follows:

    +------+------------------------------+-------------------------+
    | Pos  | DB Column                    | Source Field            |
    +======+==============================+=========================+
    | 1    | ``p_id``                     | ``id``                  |
    +------+------------------------------+-------------------------+
    | 2    | ``program``                  | ``program``             |
    +------+------------------------------+-------------------------+
    | 3    | ``university``               | ``university``          |
    +------+------------------------------+-------------------------+
    | 4    | ``comments``                 | ``comments``            |
    +------+------------------------------+-------------------------+
    | 5    | ``date_added``               | ``date_added``          |
    +------+------------------------------+-------------------------+
    | 6    | ``url``                      | ``url``                 |
    +------+------------------------------+-------------------------+
    | 7    | ``status``                   | ``status``              |
    +------+------------------------------+-------------------------+
    | 8    | ``term``                     | ``term``                |
    +------+------------------------------+-------------------------+
    | 9    | ``us_or_international``      | ``US/International``    |
    +------+------------------------------+-------------------------+
    | 10   | ``gpa``                      | ``gpa``                 |
    +------+------------------------------+-------------------------+
    | 11   | ``gre``                      | ``gre``                 |
    +------+------------------------------+-------------------------+
    | 12   | ``gre_v``                    | ``grev``                |
    +------+------------------------------+-------------------------+
    | 13   | ``gre_aw``                   | ``greaw``               |
    +------+------------------------------+-------------------------+
    | 14   | ``degree``                   | ``degree``              |
    +------+------------------------------+-------------------------+
    | 15   | ``llm_generated_program``    | ``llm-generated-program``    |
    +------+------------------------------+-------------------------+
    | 16   | ``llm_generated_university`` | ``llm-generated-university`` |
    +------+------------------------------+-------------------------+

    :param scrapedData: A list of application record dictionaries as
                        returned by :func:`clean_data`. Passed directly
                        to :func:`_createTuplesList`, which mutates
                        records in place during type coercion.
    :type scrapedData: list[dict]
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
    :raises ValueError: If :func:`_createTuplesList` fails to coerce a
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
        with psycopg.connect(**config) as conn:
            with conn.cursor() as cur:
                cur.executemany(insertSQL, _createTuplesList(scrapedData))
                conn.commit()
    finally:
        conn.close()

