import psycopg
from config import config

termCountSQL = """
SELECT COUNT(p_id) AS term_count
FROM applicants
WHERE term = 'Fall 2026';
"""

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

averageScoresSQL = """
SELECT
    (SELECT AVG(gpa) FROM applicants WHERE gpa > 0) AS avg_gpa,
    (SELECT AVG(gre) FROM applicants WHERE gre > 0) AS avg_gre,
    (SELECT AVG(gre_v) FROM applicants WHERE gre_v > 0) AS avg_gre_v,
    (SELECT AVG(gre_aw) FROM applicants WHERE gre_aw >= 0) AS avg_gre_aw
"""

averageAmericanGPASQL = """
SELECT AVG(gpa)
    FROM applicants
    WHERE us_or_international = 'American' AND gpa > 0
"""

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

averageGPAFallAcceptanceSQL = """
SELECT AVG(gpa)
FROM applicants
WHERE term = 'Fall 2026' AND gpa > 0;
"""

jhuApplicantsSQL = """
SELECT count(p_id)
FROM applicants
WHERE program LIKE '%Computer Science%' AND university LIKE '%Johns Hopkins%';
"""

universityListAcceptancesSQL = """
SELECT COUNT(p_id)
FROM applicants
WHERE extract(YEAR FROM date_added) = 2026 AND
program LIKE '%Computer Science%' AND
university LIKE ANY (ARRAY['%Georgetown University%','%Massachusetts Institute of Technology%','%MIT%','%Stanford University%','%Carnegie Mellon%'])
"""

llmUniversityListAcceptancesSQL = """
SELECT COUNT(p_id)
FROM applicants
WHERE extract(YEAR FROM date_added) = 2026 AND
llm_generated_program LIKE '%Computer Science%' AND
llm_generated_university LIKE ANY (ARRAY['%Georgetown University%','%Massachusetts Institute of Technology%','%MIT%','%Stanford University%','%Carnegie Mellon%'])
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
    with conn.cursor() as cur:
            # Q1
            cur.execute(termCountSQL)
            row = cur.fetchone()
            return row

def getInternationalAverage(conn):
    with conn.cursor() as cur:
            # Q1
            cur.execute(percentageInternationalSQL)
            row = cur.fetchone()
            return row

def getAverageScores(conn):
    with conn.cursor() as cur:
            # Q1
            cur.execute(averageScoresSQL)
            row = cur.fetchone()
            return row

def getAmericanGPA(conn):
    with conn.cursor() as cur:
            # Q1
            cur.execute(averageAmericanGPASQL)
            row = cur.fetchone()
            return row

def getFallAcceptancesPercent(conn):
    with conn.cursor() as cur:
            # Q1
            cur.execute(percentAcceptedSQL)
            row = cur.fetchone()
            return row

def getFallAcceptancesGPA(conn):
    with conn.cursor() as cur:
            # Q1
            cur.execute(averageGPAFallAcceptanceSQL)
            row = cur.fetchone()
            return row

def getJHUCSEntries(conn):
    with conn.cursor() as cur:
            # Q1
            cur.execute(jhuApplicantsSQL)
            row = cur.fetchone()
            return row

def getUniversityListAcceptances(conn):
    with conn.cursor() as cur:
            # Q1
            cur.execute(universityListAcceptancesSQL)
            row = cur.fetchone()
            return row

def getLLMUniversityListAcceptances(conn):
    with conn.cursor() as cur:
            # Q1
            cur.execute(llmUniversityListAcceptancesSQL)
            row = cur.fetchone()
            return row

def getBadGREAWScores(conn):
    with conn.cursor() as cur:
            # Q1
            cur.execute(badGREAWScoresSQL)
            row = cur.fetchone()
            return row
    
def getBadGREScores(conn):
    with conn.cursor() as cur:
            # Q1
            cur.execute(badGREScoresSQL)
            row = cur.fetchone()
            return row
    
if __name__=='__main__':
    try:
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

    except Exception as e:
        print(f"Error: {e}")

    finally:
        conn.close