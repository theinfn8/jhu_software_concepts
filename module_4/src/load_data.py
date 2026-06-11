import json
import psycopg
from src.config import config
from datetime import datetime

def _loadData():
    with open("llm_generated_applicant_data.json", 'r') as f:
        return json.load(f)

def _createTuplesList(scrapedData):
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
    try:
        with psycopg.connect(**config) as conn:
            with conn.cursor() as cur:
                cur.executemany(insertSQL, _createTuplesList(scrapedData))
                conn.commit()
    finally:
        conn.close()

if __name__=='__main__':
    try:
        with psycopg.connect(**config) as conn:
            with conn.cursor() as cur:
                cur.execute(createTableSQL)
                conn.commit()
                cur.executemany(insertSQL, _createTuplesList(_loadData()))
                conn.commit()
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
