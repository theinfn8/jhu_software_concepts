from datetime import datetime
import os
import psycopg
from dotenv import load_dotenv

def _create_tuples_list(scraped_data):
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
                        datum["degree"],
                        datum["gpa"],
                        datum["gre"],
                        datum["grev"],
                        datum["greaw"],
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
    degree text,
    gpa float,
    gre float,
    gre_v float,
    gre_aw float,
    llm_generated_program text,
    llm_generated_university text
);
"""

INSERT_SQL = """
    INSERT INTO applicants (p_id, program, university, comments, date_added, url, status,
    term, us_or_international, degree, gpa, gre, gre_v, gre_aw, llm_generated_program, llm_generated_university)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

initial_setup = [
    {"id": 1020268, "program": "Human Centered Design", "university": "Handong Global University", "comments": "None", "date_added": "May 26, 2026", "url": "https://www.thegradcafe.com/result/1020268", "status": "Accepted", "status_date": "May 26", "accepted": "None", "rejected": "None", "term": "Fall 2026", "US/International": "International", "degree": "Masters", "gpa": "3.09", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Human Centered Design", "llm-generated-university": "Handong Global University"},
    {"id": 1020267, "program": "Kinesiology", "university": "University of Toronto", "comments": "None", "date_added": "May 26, 2026", "url": "https://www.thegradcafe.com/result/1020267", "status": "Rejected", "status_date": "May 22", "accepted": "None", "rejected": "May 22", "term": "Fall 2026", "US/International": "International", "degree": "Masters", "gpa": "None", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Kinesiology", "llm-generated-university": "University of Toronto"},
    {"id": 1020266, "program": "Biomedical Engineering", "university": "University of British Columbia", "comments": "None", "date_added": "May 26, 2026", "url": "https://www.thegradcafe.com/result/1020266", "status": "Accepted", "status_date": "May 19", "accepted": "None", "rejected": "None", "term": "Fall 2026", "US/International": "International", "degree": "Masters", "gpa": "None", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Biomedical Engineering", "llm-generated-university": "University of British Columbia"},
    {"id": 1020265, "program": "Economics", "university": "Harvard University", "comments": "I have research experience and i have 2 years working", "date_added": "May 26, 2026", "url": "https://www.thegradcafe.com/result/1020265", "status": "Accepted", "status_date": "May 26", "accepted": "None", "rejected": "None", "term": "Spring 2025", "US/International": "International", "degree": "PhD", "gpa": "3.40", "gre": "170", "grev": "170", "greaw": "6.00", "llm-generated-program": "Economics", "llm-generated-university": "Harvard University"},
    {"id": 1020264, "program": "Economics", "university": "Harvard University", "comments": "None", "date_added": "May 26, 2026", "url": "https://www.thegradcafe.com/result/1020264", "status": "Accepted", "status_date": "May 26", "accepted": "None", "rejected": "None", "term": "Fall 2026", "US/International": "International", "degree": "PhD", "gpa": "3.40", "gre": "170", "grev": "170", "greaw": "6.00", "llm-generated-program": "Economics", "llm-generated-university": "Harvard University"},
    {"id": 1020263, "program": "Social Work", "university": "University of North Carolina at Chapel Hill", "comments": "I already have a recent master's in Writing Studies and Educational Psychology with a 4.0 GPA, as well as over a decade of social work experience, and several academic publications, conference presentations, and workshops that focused on therapeutic techniques, mental wellbeing, or disability. I also taught for my entire master's degree, was an Assistant Director of the Writing Center, and conducted my own 100+ participant study. I was waitlisted on March 30th, told all decisions would be final by April 24th, and then received an email offering me admission into the part-time and non-funded 3-year program (rather than the full-time, funded 2-year program I had applied for) on April 29th. I was told within the next week I would get my official offer of admission, and I had that same one week to accept it and pay the $250 admission fee. I emailed back 6 days later saying I had discussed with my support network and had decided to reject the offer due to national instability and uncertainty of gov financial aid, but would like to reapply in the future. I asked how to indicate this acceptance on a potential future application, as I had never received an official admission offer. Two weeks after that, I got my official admission offer and a host of emails telling me what my next steps were. All of them had inconsistent and contradictory information, including dates that were different email to email and deadlines that had passed weeks ago. One email had three different dates for the same (important) deadline. I finally got a response to the email I had sent directly to the Admissions Office, saying they were sorry to hear I was declining and informing me of the steps I needed to take to officially decline. They did not answer the other questions I had included in my email to them. Throughout all of this, my name was only spelled correctly once. We will see if I do end up reapplying in future years.", "date_added": "May 26, 2026", "url": "https://www.thegradcafe.com/result/1020263", "status": "Accepted", "status_date": "Apr 29", "accepted": "None", "rejected": "None", "term": "Fall 2026", "US/International": "American", "degree": "Masters", "gpa": "3.73", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Social Work", "llm-generated-university": "University of North Carolina at Chapel Hill"},
    {"id": 1020262, "program": "Pure Math", "university": "princeton", "comments": "None", "date_added": "May 25, 2026", "url": "https://www.thegradcafe.com/result/1020262", "status": "Accepted", "status_date": "May 25", "accepted": "None", "rejected": "None", "term": "Fall 2026", "US/International": "American", "degree": "PhD", "gpa": "None", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Pure Math", "llm-generated-university": "Prince Town"},
    {"id": 1020261, "program": "Physics", "university": "University of Idaho", "comments": "None", "date_added": "May 24, 2026", "url": "https://www.thegradcafe.com/result/1020261", "status": "Rejected", "status_date": "Apr 28", "accepted": "None", "rejected": "Apr 28", "term": "Fall 2026", "US/International": "American", "degree": "PhD", "gpa": "None", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Physics", "llm-generated-university": "University of Idaho"},
    {"id": 1020260, "program": "Physics", "university": "University of Toledo", "comments": "None", "date_added": "May 24, 2026", "url": "https://www.thegradcafe.com/result/1020260", "status": "Rejected", "status_date": "May 15", "accepted": "None", "rejected": "May 15", "term": "Fall 2026", "US/International": "American", "degree": "PhD", "gpa": "None", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Physics", "llm-generated-university": "University of Toledo"},
    {"id": 1020259, "program": "Physics", "university": "University of Texas at Arlington", "comments": "None", "date_added": "May 24, 2026", "url": "https://www.thegradcafe.com/result/1020259", "status": "Rejected", "status_date": "May 23", "accepted": "None", "rejected": "May 23", "term": "Fall 2026", "US/International": "American", "degree": "PhD", "gpa": "None", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Physics", "llm-generated-university": "The University of Texas at Arlington"},
    {"id": 1020258, "program": "Economics", "university": "Texas Tech University", "comments": "I have published Q1 two research paper.", "date_added": "May 24, 2026", "url": "https://www.thegradcafe.com/result/1020258", "status": "Accepted", "status_date": "Apr 17", "accepted": "None", "rejected": "None", "term": "Fall 2026", "US/International": "International", "degree": "Masters", "gpa": "3.45", "gre": "165", "grev": "165", "greaw": "5.00", "llm-generated-program": "Economics", "llm-generated-university": "Texas Tech University"},
    {"id": 1020257, "program": "Computer Science", "university": "University of Utah", "comments": "None", "date_added": "May 24, 2026", "url": "https://www.thegradcafe.com/result/1020257", "status": "Rejected", "status_date": "May 23", "accepted": "None", "rejected": "May 23", "term": "Fall 2026", "US/International": "International", "degree": "PhD", "gpa": "3.88", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Computer Science", "llm-generated-university": "University of Utah"},
    {"id": 1020256, "program": "Social Work", "university": "University of Toronto", "comments": "Accepted off of waitlist for 2 year/foundational stream", "date_added": "May 24, 2026", "url": "https://www.thegradcafe.com/result/1020256", "status": "Accepted", "status_date": "Apr 24", "accepted": "None", "rejected": "None", "term": "Fall 2026", "US/International": "Other", "degree": "Masters", "gpa": "4.00", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Social Work", "llm-generated-university": "University of Toronto"},
    {"id": 1020255, "program": "Social Work, Regular Stream", "university": "Wilfrid Laurier University", "comments": "None", "date_added": "May 24, 2026", "url": "https://www.thegradcafe.com/result/1020255", "status": "Accepted", "status_date": "May 15", "accepted": "None", "rejected": "None", "term": "Fall 2026", "US/International": "Other", "degree": "Masters", "gpa": "4.00", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Social Work, Regular Stream", "llm-generated-university": "Wilfrid Laurier University"},
    {"id": 1020254, "program": "Architecture", "university": "University of Washington", "comments": "Got admitted off the waitlist and I'm very excited!", "date_added": "May 24, 2026", "url": "https://www.thegradcafe.com/result/1020254", "status": "Accepted", "status_date": "May 22", "accepted": "None", "rejected": "None", "term": "Fall 2026", "US/International": "International", "degree": "Masters", "gpa": "3.62", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Architecture", "llm-generated-university": "University of Washington"},
    {"id": 1020253, "program": "Computational And Applied Mathematics", "university": "University of Chicago", "comments": "None", "date_added": "May 23, 2026", "url": "https://www.thegradcafe.com/result/1020253", "status": "Accepted", "status_date": "May 22", "accepted": "None", "rejected": "None", "term": "Fall 2026", "US/International": "American", "degree": "Masters", "gpa": "3.47", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Computational And Applied Mathematics", "llm-generated-university": "University of Chicago"},
    {"id": 1020252, "program": "Hospitality And Tourism Management", "university": "Islamic Azad University Science and Research Branch", "comments": "None", "date_added": "May 23, 2026", "url": "https://www.thegradcafe.com/result/1020252", "status": "Wait listed", "status_date": "Sep 26", "accepted": "None", "rejected": "None", "term": "Fall 2026", "US/International": "International", "degree": "Masters", "gpa": "4.00", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Hospitality And Tourism Management", "llm-generated-university": "Islamic Azad University Science And Research Branch"},
    {"id": 1020251, "program": "Computer Science", "university": "University of British Columbia", "comments": "None", "date_added": "May 23, 2026", "url": "https://www.thegradcafe.com/result/1020251", "status": "Rejected", "status_date": "May 22", "accepted": "None", "rejected": "May 22", "term": "Fall 2026", "US/International": "International", "degree": "Masters", "gpa": "3.85", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "", "llm-generated-university": "University of British Columbia"},
    {"id": 1020250, "program": "Astrophysics", "university": "Rochester Institute of Technology", "comments": "None", "date_added": "May 23, 2026", "url": "https://www.thegradcafe.com/result/1020250", "status": "Rejected", "status_date": "May 05", "accepted": "None", "rejected": "May 05", "term": "Fall 2026", "US/International": "International", "degree": "PhD", "gpa": "3.86", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Astrophysics", "llm-generated-university": "Rochester Institute of Technology"},
    {"id": 1020249, "program": "Political Science", "university": "University of Houston", "comments": "None", "date_added": "May 23, 2026", "url": "https://www.thegradcafe.com/result/1020249", "status": "Accepted", "status_date": "Apr 24", "accepted": "None", "rejected": "None", "term": "Fall 2026", "US/International": "International", "degree": "PhD", "gpa": "None", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Political Science", "llm-generated-university": "University of Houston"}
]

def get_config():
    load_dotenv()
    config = {
        "host" : os.getenv("DB_HOST"),
        "port" : os.getenv("DB_PORT"),
        "dbname" : os.getenv("DB_NAME"),
        "user" : os.getenv("DB_USER"),
        "password" : os.getenv("DB_PASSWORD")
    }
    print(config)
    return config

try:
    with psycopg.connect(**get_config()) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS applicants")
            cur.execute(CREATE_TABLE_SQL)
            conn.commit()
            cur.executemany(INSERT_SQL, _create_tuples_list(initial_setup))
            conn.commit()
except Exception as e:
    print(f"Error: {e}")
