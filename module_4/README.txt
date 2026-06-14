Name: Chris Carson, ccarso12
Module Info: Module 4, Testing and Documentation, Due Sunday by 23:59
Instructions: install python requirements from requirements.txt
    Make sure the postgreSQL database is running
    Create .env in src directory (excluded this time per assignment requirements)
    Update the server info in .env
        host=localhost
        port=5432
        dbname=gradcafe
        user=<your username>
        password=<your password>
    Run load_data.py to create the table and import data from llm_generated_applicant_data.json,
        located in the same directory
    Run run.py to start the Flask server, connect on localhost in your browser
    Run pytest to conduct testing
Approach: The assignment required some changes to the code to match the requirements as written and
    I spent most of the first day getting the factory setup and the new structure functioning again
    for testing.

    There were some graded items that I couldn't include in the testing exactly as written, based
    on my original implementation. For example, I didn't opt to use environment variables, but the
    excludable .env file method of securing the server data. The config is still just as mockable
    as the environment variable though, and pushed with that so as to not make any more major
    changes to the code.