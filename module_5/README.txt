Name: Chris Carson, ccarso12
Module Info: Module 4, Testing and Documentation, Due Sunday by 23:59
Instructions: install python requirements from requirements.txt
    Make sure the postgreSQL database is running
    Create environment variables based on format in .env.example. Note there are separate variables
        for the normal server access and for the test server and both sets are needed to run all
        parts.
    
    Run run.py to start the Flask server, connect on localhost in your browser
    Run pytest to conduct testing
Approach: I attacked this in a top to bottom methodology, step 1 through to the end. Running pylint
    got me mostly issues with variable names. I was persistent in my naming convention (camel case,
    since I mostly work in Java) so I renamed all of my variables and functions and then worked
    through any items that were remaining. Getting pytest to run successfully afterwards was a bit
    more of an effort, but I managed to work it out.

    Step 2 had me wondering if there was much I needed to change. In the end, I added a LIMIT to
    each of the static SQL statements. The dynamic portion was already using a parameter list and
    there were no dynamically generated Identifiers (columns or table names) in the only dynamic
    SQL statement (the insert). I couldn't think of a reason why there would need to be and left it
    as is.

    Step 3 I made the environment variable change that I knew I would need to make since the end of
    the last module. I re-used the config.py to generalize better for directing to the test db and
    generated environment variables from the .env. This means seperate .env files for test and
    production, but that is an acceptable seperation to me.
    
    I originally built the database with a second user with less access in mind, since that is
    normal operating procedure. I just reduced the permissions on the user with pgAdmin and tested
    to ensure it still ran.

    Step 4 

    Step 5 I have been updating requirements.txt as I have been adding functionality. It is also
    used in the github action on push, so testing in the CI pipeline would fail if there were any
    missing requirements.

    After reading up on setup.py I added the setup.py and a setup.cfg to allow installs.

    Step 6

    Step 7


References: The most difficult parts of this assignment were the Github Actions portion. I found
    the following items useful, but most of the information online is misleading about using Github
    environment variables/secrets. Everything is written as if it "just works" when that is most
    decidedly not true.

    Helpful for adding files into the commit (the SVG) in this case:
    https://joht.github.io/johtizen/build/2022/01/20/github-actions-push-into-repository.html

    For general github and github actions, Chapter 12 - Working with Git and GitHub Actions:
    Saha, A. (2024, April) Django in Production, Packt Publishing Ltd.

    For the setup.py file I sourced the following from my collection, Chapter 5 - Distributing Your
    Software:
    Danjou, J. (2019) Serious Python, No Starch Press
