Name: Chris Carson, ccarso12
Module Info: Module 4, Testing and Documentation, Due Sunday by 23:59
Instructions: install python requirements from requirements.txt
    Make sure the postgreSQL database is running
    Create .env in src directory (excluded this time per assignment requirements)
    Create the server info in ./src/.env for the real server, and one in ./tests/.env for the
    testing environment:
        host=localhost
        port=5432
        dbname=gradcafe
        user=<your username>
        password=<your password>
    Run run.py to start the Flask server, connect on localhost in your browser
    Run pytest to conduct testing
Approach: The assignment required some changes to the code to match the requirements as written and
    I spent a large piece of time getting the factory setup and the new structure functioning again
    for testing.

    There were some graded items that I couldn't include in the testing exactly as written, based
    on my original implementation. For example, I didn't opt to use environment variables, but the
    excludable .env file method of securing the server data. The config is still just as mockable
    as the environment variable though, and pushed with that so as to not make any more major
    changes to the code.

    Once I had the restructure completed, I setup a docker-based test server for use during
    testing. Since conftest.py is run before any of the other test files, I created setup for the
    test server so that I would know exactly what was in the database for testing. Then I proceeded
    through the list of required testing functions in the assignment. I created some fixtures to
    mock common returns so I wouldn't need to repeat them and to redirect the code to the test
    server.

    Next I moved to using an LLM to generate the Sphinx entries, checking for incorrect information
    and making corrections as needed. Finally I added the github action for automating testing.