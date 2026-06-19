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
    the last module. For ease of conversion and less repeat code, I opted to re-use the config.py
    to serve a dictionary of the connection items, just like my previous version. This reduced code
    changes required per connection command. I then added the environment variables and tested the
    connection. I originally built the database with a second user with less access, since that is
    normal operating procedure. I just reduced the permissions on the user with pgAdmin.

    