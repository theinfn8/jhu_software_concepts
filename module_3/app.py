from flask import Flask, render_template
import psycopg
import query_data
from config import config

app = Flask(__name__, static_folder="static", template_folder="templates")
updating = False

@app.route('/')
def home():
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
    return render_template("index.html",
                           q1Answer=q1Answer,
                           q2Answer=q2Answer,
                           q3Answer=q3Answer,
                           q4Answer=q4Answer,
                           q5Answer=q5Answer,
                           q6Answer=q6Answer,
                           q7Answer=q7Answer,
                           q8Answer=q8Answer,
                           q9Answer=q9Answer,
                           q10Answer=q10Answer,
                           q11Answer=q11Answer)

@app.route('/api/entries', methods=['GET'])
def updateDatabase():
    if updating:
        return {"status": "Updating"}
    
    updating = True
    

if __name__=='__main__':
    app.run(host='0.0.0.0', port=8080)