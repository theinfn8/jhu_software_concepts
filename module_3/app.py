from flask import Flask, render_template
import psycopg
import query_data
from config import config
from scrape import scrape_data
from load_data import insertEntries

app = Flask(__name__, static_folder="static", template_folder="templates")
updating = False

def getAnalysisHTML():
    with psycopg.connect(**config) as conn:
        q1Answer = query_data.getTermCount(conn)[0]
        q2Answer = query_data.getInternationalAverage(conn)[0]
        q3Rows = query_data.getAverageScores(conn)
        q3Answer = f"GPA: {q3Rows[0]}, GRE: {q3Rows[1]}, GRE-V: {q3Rows[2]}, GRE-AW: {q3Rows[3]}"
        q4Answer = query_data.getAmericanGPA(conn)[0]
        q5Answer = query_data.getFallAcceptancesPercent(conn)[0]
        q6Answer = query_data.getFallAcceptancesGPA(conn)[0]
        q7Answer = query_data.getJHUCSEntries(conn)[0]
        q8Answer = query_data.getUniversityListAcceptances(conn)[0]
        q9Answer = query_data.getLLMUniversityListAcceptances(conn)[0]
        q10Answer = query_data.getBadGREAWScores(conn)[0]
        q11Answer = query_data.getBadGREScores(conn)[0]

    return f"""<ul>
            <li>
                <h4>1. How many entries do you have in your database who have applied for Fall 2026?</h4>
                <p class="smalltext">Answer: {q1Answer}</p>
            </li>
            <li>
                <h4>2. What percentage of entries are from international students (not American or Other) (to two decimal places)?</h4>
                <p class="smalltext">Answer: {q2Answer}</p>
            </li>
            <li>
                <h4>3. What is the average GPA, GRE, GRE V, GRE AW of applicants who provide these metrics?</h4>
                <p class="smalltext">Answer: {q3Answer}</p>
            </li>
            <li>
                <h4>4. What is their average GPA of American students in Fall 2026?</h4>
                <p class="smalltext">Answer: {q4Answer}</p>
            </li>
            <li>
                <h4>5. What percent of entries for Fall 2026 are Acceptances (to two decimal places)?</h4>
                <p class="smalltext">Answer: {q5Answer}</p>
            </li>
            <li>
                <h4>6. What is the average GPA of applicants who applied for Fall 2026 who are Acceptances?</h4>
                <p class="smalltext">Answer: {q6Answer}</p>
            </li>
            <li>
                <h4>7. How many entries are from applicants who applied to JHU for a masters degrees in Computer Science?</h4>
                <p class="smalltext">Answer: {q7Answer}</p>
            </li>
            <li>
                <h4>8. How many entries from 2026 are acceptances from applicants who applied to Georgetown University, MIT, Stanford University, or Carnegie Mellon University for a PhD in Computer Science?</h4>
                <p class="smalltext">Answer: {q8Answer}</p>
            </li>
            <li>
                <h4>9. Do you numbers for question 8 change if you use LLM Generated Fields (rather than your downloaded fields)?</h4>
                <p class="smalltext">Answer: {q9Answer}</p>
            </li>
            <li>
                <h4>10. How many GRE AW scores reported exceeded the maximum score attainable?</h4>
                <p class="smalltext">Answer: {q10Answer}</p>
            </li>
            <li>
                <h4>11. How many GRE scores reported exceeded the maximum score attainable?</h4>
                <p class="smalltext">Answer: {q11Answer}</p>
            </li>
        </ul>"""

@app.route('/')
def home():
    return render_template("base.html")

@app.route('/api/entries', methods=['GET'])
def updateDatabase():
    global updating
    # If updating, send blocking response
    if updating:
        return {"status": "Updating"}
    
    updating = True
    
    lastIDFetched = 1
    with psycopg.connect(**config) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(p_id) FROM applicants")
            lastIDFetched = cur.fetchone()[0] # Mark where we left off last time
    conn.close()
    
    scrapedData = scrape_data(lastIDFetched)
    
    # If there were new entries, update the database, update the last ID (which should be the first item in the list)
    if scrapedData != None:
        if len(scrapedData) > 0:
            insertEntries(scrapedData)
            lastIDFetched = scrapedData[0]["id"]

    updating = False
    return {"status": "Available",
            "maxID": f"{lastIDFetched}"}

@app.route('/api/analysis', methods=['GET'])
def updateAnalysis():
    global updating

    # If updating the database, send blocking response
    if updating:
        return {"status": "Updating"}

    # Else, build the HTML and send it out
    returnHTML = getAnalysisHTML()
    
    return {"status": "Available",
            "content": returnHTML}

if __name__=='__main__':
    app.run(host='0.0.0.0', port=8080)