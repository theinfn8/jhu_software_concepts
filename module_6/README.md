## __Module 6__

### __Name__: Chris Carson
### __Module Info__: Module 6, Deploy Anywhere

### __Summary__:
A web app that calculates some statistics on data scraped from The Grad Cafe that has been cleaned and stored in a Postgres database. The front end uses flask with HTML, CSS, and Javascript. Requests are queued to RabbitMQ and picked up by an independent worker. The worker checks the queued item against a task map and executes the appropriate function. While in progress, the worker updates the status of the task in a tracker. The front-end polls a tracking API to check for task completion. The whole web app stack is rolled into Docker images for easier deployment.

### __Installation and Running__:
The .env files for the separate services need to contain data updated for their individual environments. Example files are included for each and need to be renamed without the example ending to function properly. Update the .env.db file with the lower privilege user name and password for creation in the database in the DB_USER and USER_PASS environment variables. Update the .env.web and .env.worker files to match (or go extra and add your own code for split user functionality). If you have a need, the ports opened by docker can be remapped with WEB_PORT and RMW_MGMT_PORT. Afterwards, everything should run on:\
`docker compose up --build`
Browse to: http://localhost:8080 for the app
Available End-Points:
/
/health
POST /api/pull-data
POST/GET /api/analysis
GET /api/tasks/<id>

### __Approach__:
I moved the environment variables out into environment variable files to keep the compose file cleaner, separate environment variables from the various services so there is no data spillage (ie you can't get the admin info for the database by attacking the web app) and to generally make it easier to "run anywhere". I created an additional service that runs once and checks that the necessary startup data is present and in the form expected. I exported my database information from the previous postgres, and added the code for creating the grad_user role and permissions. I added environment variables to create a rabbitmq user, so I could create a rabbitmq connection URL (and the documentation indicates guest would not work over the docker network).
    
I then started adjusting the web app and worker code to run enough to get rabbitmq and postgres running to validate those were functioning as intended. I then worked on the producer code to connect to the rabbitmq server. I added the mapping of the root page to /analysis, and pulled the HTML for the analysis by hand in the code so it loads directly on the page, per earlier feedback.

Once that was complete I moved to the worker code. I started with the rabbitmq connection portion, which checks the message for mapping and dispatches to the appropriate function. Some of the modular design from the previous iteration became obsolete, so I moved some of the database write code into worker and added some more robust error detection. Functions pass up exceptions so they can be addressed at the higher level accordingly, included providing the required basic_nack on failure.

At this point, I wasn't sure how to to accomplish the recomputation of the analysis portion and make it matter to the code. I opted to create a materialized view in the postgres server, so I went back to the migration piece and added it into the setup. This allows me to make the analysis button update the view, so it can be used to update the presentation to the user. It also helped clean up the HTML creation portion of the code.

I moved from there to testing that everything would work as a whole product and hammered out all of the bugs that were left. Then moved to running the linter and cleaning up the code. And this caused me some issues. Every time I "fixed" an import that pleased the linter, it broke the code. Every time I changed the code to make the program run, it broke the linter. After a very frustrating time, I realized that each of the individual apps needed to be treated as such and called the individual applications with pylint and then it recognized the imports. Super frustrating.

I came back and updated the scraping functionality that had changed since the last time I ran it and made the error handling more robust, including adding an API to give a health check of the services. Adjusted the restart policy and added the task-status tracking functionality.
