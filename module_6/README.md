Name: Chris Carson, ccarso12
Module Info: Module 6, Deploy Anywhere, Due Sunday by 23:59
Fresh Install:
    The .env files for the seperate services need to contain data updated for their individual
    environments. Example files included for each. Make sure to update the .env.db file with
    the lower privlege user name and password for creation in the database in DB_USER and
    USER_PASS.
    Afterwards, everything should run on: docker compose up --build

Approach: I new I would be traveling the first part of this week, so I saved the assignment as a
    pdf and worked on the initial docker setup, adjusting the project layout, and the data
    migration. I moved the environment variables out into a environment variable files to keep the
    compose file cleaner, separate environment variables from the various services so there is no
    data spillage (ie you can't get the admin info for the database by attacking the web app) and
    to generally make it easier to "run anywhere". I created an additional service that runs once
    and checks that the necessary startup data is present and in the form expected. I exported my
    database information from my previous postgres, added the code for creating the grad_user role
    and permissions, and mirrored it into the postgres init script. I added environment variables
    to create a rabbitmq user, so I could create a rabbitmq connection URL (and the documentation
    indicates guest wouldn't work over the docker network).

    I then started adjusting the web app and worker code to run enough to get rabbitmq and postgres
    running to validate those were function as intended. I then worked on the producer code to
    connect to the rabbitmq server. I added the mapping of the root page to /analysis, and pulled
    the HTML for the analysis by hand in the code so it loads directly on the page, per feedback
    from module 4

    Once that was complete I moved to the worker code. I started with the rabbitmq connection
    portion, which checks the message for mapping and dispatches to the appropriate function. Some
    of the modular design from the previous iteration became obsolete, so I moved some of the
    database write code into worker and added some more robust error detection. Functions pass up
    exceptions so they can be addressed at the higher level accordingly, included providing the
    required basic_nack on failure.

    At this point, I wasn't sure how to to accomplish the recomputation of the analysis portion and
    make it matter to the code. I opted to create a materialized view in the postgres server, so I
    went back to the migration piece and added it into the setup. This allows me to make the
    analysis button update the view, so it can be used to update the presentation to the user. It
    also helped clean up the HTML creation portion of the code.

    I moved from there to testing that everything would work as a whole product and hammered out
    all of the bugs that were left. Then moved to running the linter and cleaning up the code. And
    this caused me some issues. Every time I "fixed" an import that pleased the linter, it broke
    the code. Every time I changed the code to make the program run, it broke the linter. After a
    very frustrating time, I realized that each of the individual apps needed to be treated as such
    and called the individual applications with pylint and then it recognized the imports. Super
    frustrating.

    Updated the github action to point to module 6, minus the graph. Then I worked the dockerhub
    portion of the assignment. I pushed a second copy to make sure everything ran independently
    as expected, then created a dockerhub account and pushed the three containers up.
    

References: 
