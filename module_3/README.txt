Name: Chris Carson, ccarso12
Module Info: Module 3, Database Queries, Due Sunday by 23:59
Instructions: install python requirements from requirements.txt
    Make sure the postgreSQL database is running
    Update the server info in .env (only included for ease of running)
    Run load_data.py to create the table and import data from llm_generated_applicant_data.json,
        located in the same directory
    Run query_data.py to view the questions and answers from SQL queries
    Run app.py to start the Flask server, connect on localhost in your browser
Approach: I focused on the database creation first, starting with the SQL for the table and the
    insert. Then I moved to the Python import to the database and created load_data.py. I wrote the
    insert function to enable the web app to easily insert new entries for the udpate feature.

    I then focused on creating the SQL queries to answer the questions. I went with a purely SQL
    based solution for this to simplify the Python code (and work my SQL skills). I created the
    query_data file and added in the code. After completing this, I cleaned the code up, presented
    the data better, and pushed to Git. Or thought I did. I realized I had made an error with the
    gitignore and my commit had been trying to push the model for the LLM up and failing the
    commit. A day later I had the situation fixed and the repository properly updated.

    Then I wrote the Flask app, focusing on presenting the analysis first, then moving on to the
    update portion. I opted to add an api to start the data update and the analysis update. Since I
    was dynamically loading the analysis, I opted to call the load automatically on page load and
    refactored the rest of the Flask code to adjust for it. I chose to return HTML in the JSON
    response to make my life easier (mostly I dislike working with javascript). I guess that
    technically makes this a single page web app.