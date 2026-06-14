import psycopg
from src.config import config

# Q1
termCountSQL = """
SELECT COUNT(p_id) AS term_count
FROM applicants
WHERE term = 'Fall 2026';
"""
# Q2
percentageInternationalSQL = """
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
    );
"""

# Q3
averageScoresSQL = """
SELECT
    (SELECT AVG(gpa) FROM applicants WHERE gpa > 0) AS avg_gpa,
    (SELECT AVG(gre) FROM applicants WHERE gre > 0) AS avg_gre,
    (SELECT AVG(gre_v) FROM applicants WHERE gre_v > 0) AS avg_gre_v,
    (SELECT AVG(gre_aw) FROM applicants WHERE gre_aw >= 0) AS avg_gre_aw;
"""

# Q4
averageAmericanGPASQL = """
SELECT AVG(gpa)
    FROM applicants
    WHERE us_or_international = 'American'
    AND gpa > 0
    AND term = 'Fall 2026';
"""

# Q5
percentAcceptedSQL = """
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
    );
"""

# Q6
averageGPAFallAcceptanceSQL = """
SELECT AVG(gpa)
FROM applicants
WHERE term = 'Fall 2026'
AND status = 'Accepted'
AND gpa > 0;
"""

# Q7
jhuApplicantsSQL = """
SELECT count(p_id)
FROM applicants
WHERE program LIKE '%Computer Science%'
AND university LIKE '%Johns Hopkins%'
AND degree = 'Masters';
"""

# Q8
universityListAcceptancesSQL = """
SELECT COUNT(p_id)
FROM applicants
WHERE extract(YEAR FROM date_added) = 2026
AND degree = 'PhD'
AND program LIKE '%Computer Science%'
AND university LIKE ANY (ARRAY['%Georgetown University%','%Massachusetts Institute of Technology%','%MIT%','%Stanford University%','%Carnegie Mellon%'])
AND status = 'Accepted';
"""

llmUniversityListAcceptancesSQL = """
SELECT COUNT(p_id)
FROM applicants
WHERE extract(YEAR FROM date_added) = 2026
AND degree = 'PhD'
AND llm_generated_program LIKE '%Computer Science%'
AND llm_generated_university LIKE ANY (ARRAY['%Georgetown University%','%Massachusetts Institute of Technology%','%MIT%','%Stanford University%','%Carnegie Mellon%'])
AND status = 'Accepted';
"""

badGREAWScoresSQL = """
SELECT COUNT(p_id)
FROM applicants
WHERE gre_aw > 6
"""

badGREScoresSQL = """
SELECT COUNT(p_id)
FROM applicants
WHERE gre > 340
"""

def getTermCount(conn):
    """
    Query the count of applicant entries for Fall 2026.

    Executes ``termCountSQL`` against the provided database connection
    and returns the first row of the result.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`getStats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the count of Fall 2026
              entries, e.g. ``(142,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
            # Q1
            cur.execute(termCountSQL)
            row = cur.fetchone()
            return row

def getInternationalAverage(conn):
    """
    Query the percentage of applicant entries from international students.

    Executes ``percentageInternationalSQL`` against the provided database
    connection. Excludes applicants categorised as American or Other.
    Returns the percentage rounded to two decimal places.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`getStats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the international
              applicant percentage, e.g. ``(34.57,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
            # Q2
            cur.execute(percentageInternationalSQL)
            row = cur.fetchone()
            return row

def getAverageScores(conn):
    """
    Query the average GPA, GRE, GRE Verbal, and GRE Analytical Writing
    scores across all applicants who reported each metric.

    Executes ``averageScoresSQL`` against the provided database connection.
    Sentinel values of ``-1.0`` representing missing scores are excluded
    from each average independently, so applicant counts may differ across
    metrics.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`getStats`.
    :type conn: psycopg.Connection
    :returns: A four-element tuple of the form
              ``(avg_gpa, avg_gre, avg_gre_v, avg_gre_aw)``, e.g.
              ``(3.72, 320.1, 158.4, 4.1)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
            # Q3
            cur.execute(averageScoresSQL)
            row = cur.fetchone()
            return row

def getAmericanGPA(conn):
    """
    Query the average GPA of American applicants for Fall 2026.

    Executes ``averageAmericanGPASQL`` against the provided database
    connection. Filters to applicants whose ``us_or_international``
    field is ``American`` and whose ``term`` is Fall 2026. Excludes
    sentinel GPA values of ``-1.0``.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`getStats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the average GPA, e.g.
              ``(3.68,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
            # Q4
            cur.execute(averageAmericanGPASQL)
            row = cur.fetchone()
            return row

def getFallAcceptancesPercent(conn):
    """
    Query the percentage of Fall 2026 entries that are acceptances.

    Executes ``percentAcceptedSQL`` against the provided database
    connection. Filters to entries whose ``term`` is Fall 2026 and
    returns the acceptance rate rounded to two decimal places.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`getStats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the acceptance
              percentage, e.g. ``(21.43,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
            # Q5
            cur.execute(percentAcceptedSQL)
            row = cur.fetchone()
            return row

def getFallAcceptancesGPA(conn):
    """
    Query the average GPA of accepted applicants for Fall 2026.

    Executes ``averageGPAFallAcceptanceSQL`` against the provided
    database connection. Filters to entries whose ``term`` is Fall 2026
    and whose ``status`` is ``Accepted``. Excludes sentinel GPA values
    of ``-1.0``.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`getStats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the average GPA of
              accepted Fall 2026 applicants, e.g. ``(3.81,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
            # Q6
            cur.execute(averageGPAFallAcceptanceSQL)
            row = cur.fetchone()
            return row

def getJHUCSEntries(conn):
    """
    Query the count of entries from applicants who applied to Johns
    Hopkins University for a degree in Computer Science.

    Executes ``jhuApplicantsSQL`` against the provided database
    connection. Filters on the raw scraped ``university`` and
    ``program`` fields.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`getStats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the count of matching
              entries, e.g. ``(17,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
            # Q7
            cur.execute(jhuApplicantsSQL)
            row = cur.fetchone()
            return row

def getUniversityListAcceptances(conn):
    """
    Query the count of 2026 Computer Science acceptances at a fixed
    list of target universities using raw scraped fields.

    Executes ``universityListAcceptancesSQL`` against the provided
    database connection. Filters on the raw scraped ``university`` and
    ``program`` fields for Georgetown University, MIT, Stanford
    University, and Carnegie Mellon University. Compare with
    :func:`getLLMUniversityListAcceptances` to assess the impact of
    LLM-based name normalisation.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`getStats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the count of matching
              acceptances, e.g. ``(23,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
            # Q8
            cur.execute(universityListAcceptancesSQL)
            row = cur.fetchone()
            return row

def getLLMUniversityListAcceptances(conn):
    """
    Query the count of 2026 Computer Science acceptances at a fixed
    list of target universities using LLM-generated normalised fields.

    Executes ``llmUniversityListAcceptancesSQL`` against the provided
    database connection. Identical in scope to
    :func:`getUniversityListAcceptances` but filters on
    ``llm_generated_university`` and ``llm_generated_program`` rather
    than the raw scraped fields. Discrepancies between the two results
    indicate normalisation gaps in the raw data.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`getStats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the count of matching
              acceptances using LLM-normalised fields, e.g. ``(27,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
            # Q9
            cur.execute(llmUniversityListAcceptancesSQL)
            row = cur.fetchone()
            return row

def getBadGREAWScores(conn):
    """
    Query the count of GRE Analytical Writing scores that exceed the
    maximum attainable score.

    Executes ``badGREAWScoresSQL`` against the provided database
    connection. The GRE AW section is scored on a scale of 0.0 to 6.0
    in 0.5 increments; any value above 6.0 is considered invalid. Excludes
    sentinel values of ``-1.0``.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`getStats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the count of invalid GRE
              AW scores, e.g. ``(4,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
            # Q10
            cur.execute(badGREAWScoresSQL)
            row = cur.fetchone()
            return row
    
def getBadGREScores(conn):
    """
    Query the count of GRE total scores that exceed the maximum
    attainable score.

    Executes ``badGREScoresSQL`` against the provided database
    connection. The GRE composite score has a maximum of 340 (Verbal
    170 + Quantitative 170); any value above 340 is considered invalid.
    Excludes sentinel values of ``-1.0``.

    :param conn: An active psycopg database connection, typically opened
                 and managed by :func:`getStats`.
    :type conn: psycopg.Connection
    :returns: A single-element tuple containing the count of invalid GRE
              scores, e.g. ``(2,)``.
    :rtype: tuple
    """
    with conn.cursor() as cur:
            # Q11
            cur.execute(badGREScoresSQL)
            row = cur.fetchone()
            return row
    
def getStats():
    """
    Query the database and print a suite of descriptive statistics about
    the scraped graduate application dataset.

    Opens a single database connection using the module-level ``config``
    dictionary and executes eleven predefined analytical queries by
    delegating to dedicated query functions. Results are printed to
    stdout in a numbered format. No value is returned.

    **Queries executed:**

    +-----+---------------------------------------------------------------+----------------------------------+
    | No. | Question                                                      | Delegated to                     |
    +=====+===============================================================+==================================+
    | 1   | Count of entries for Fall 2026                                | :func:`getTermCount`             |
    +-----+---------------------------------------------------------------+----------------------------------+
    | 2   | Percentage of international applicants (to 2 d.p.)            | :func:`getInternationalAverage`  |
    +-----+---------------------------------------------------------------+----------------------------------+
    | 3   | Average GPA, GRE, GRE V, and GRE AW across all               | :func:`getAverageScores`         |
    |     | applicants who reported each metric                           |                                  |
    +-----+---------------------------------------------------------------+----------------------------------+
    | 4   | Average GPA of American applicants for Fall 2026              | :func:`getAmericanGPA`           |
    +-----+---------------------------------------------------------------+----------------------------------+
    | 5   | Percentage of Fall 2026 entries that are acceptances          | :func:`getFallAcceptancesPercent`|
    |     | (to 2 d.p.)                                                   |                                  |
    +-----+---------------------------------------------------------------+----------------------------------+
    | 6   | Average GPA of accepted Fall 2026 applicants                  | :func:`getFallAcceptancesGPA`    |
    +-----+---------------------------------------------------------------+----------------------------------+
    | 7   | Count of JHU Computer Science master's degree entries         | :func:`getJHUCSEntries`          |
    +-----+---------------------------------------------------------------+----------------------------------+
    | 8   | Count of 2026 CS PhD acceptances at Georgetown, MIT,          | :func:`getUniversityListAcceptances`  |
    |     | Stanford, or Carnegie Mellon (raw scraped fields)             |                                  |
    +-----+---------------------------------------------------------------+----------------------------------+
    | 9   | Same as Q8 using LLM-generated university and program         | :func:`getLLMUniversityListAcceptances` |
    |     | fields instead of raw scraped fields                          |                                  |
    +-----+---------------------------------------------------------------+----------------------------------+
    | 10  | Count of GRE AW scores exceeding the maximum attainable       | :func:`getBadGREAWScores`        |
    +-----+---------------------------------------------------------------+----------------------------------+
    | 11  | Count of GRE scores exceeding the maximum attainable          | :func:`getBadGREScores`          |
    +-----+---------------------------------------------------------------+----------------------------------+

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
    with psycopg.connect(**config) as conn:
        # Q1
        print('1. How many entries do you have in your database who have applied for Fall 2026?')
        print(getTermCount(conn)[0])
        # Q2
        print('2. What percentage of entries are from international students (not American or Other) (to two decimal places)?')
        print(getInternationalAverage(conn)[0])
        # Q3
        print('3. What is the average GPA, GRE, GRE V, GRE AW of applicants who provide these metrics?')
        averages = getAverageScores(conn)
        print(f"GPA: {averages[0]}, GRE: {averages[1]}, GRE V: {averages[2]}, GRE AW: {averages[3]}")
        # Q4
        print('4. What is their average GPA of American students in Fall 2026?')
        print(getAmericanGPA(conn)[0])
        # Q5
        print('5. What percent of entries for Fall 2026 are Acceptances (to two decimal places)?')
        print(getFallAcceptancesPercent(conn)[0])
        # Q6
        print('6. What is the average GPA of applicants who applied for Fall 2026 who are Acceptances?')
        print(getFallAcceptancesGPA(conn)[0])
        # Q7
        print('7. How many entries are from applicants who applied to JHU for a masters degrees in Computer Science?')
        print(getJHUCSEntries(conn)[0])
        # Q8
        print('8. How many entries from 2026 are acceptances from applicants who applied to Georgetown University, MIT, Stanford University, or Carnegie Mellon University for a PhD in Computer Science?')
        print(getUniversityListAcceptances(conn)[0])
        # Q9
        print('9. Do you numbers for question 8 change if you use LLM Generated Fields (rather than your downloaded fields)?')
        print(getLLMUniversityListAcceptances(conn)[0])
        # Q10
        print('10. How many GRE AW scores reported exceeded the maximum score attainable?')
        print(getBadGREAWScores(conn)[0])
        # Q11
        print('11. How many GRE scores reported exceeded the maximum score attainable?')
        print(getBadGREScores(conn)[0])