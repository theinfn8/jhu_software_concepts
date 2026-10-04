Name: Chris Carson, ccarso12
Module Info: Module 7, Cloud Computing Assignment, Due Sunday by 23:59

Approach:
    The EC2 server creation was no problem, and went exactly as the directions implied. I stashed
    the SSH key in my .ssh directory (as you do) and I connected directly with ssh (ssh -i
    ~./.ssh/Module_7.pem ubuntu@23.20.142.10). I used the directions provided to install docker,
    but compose has been migrated to "docker-compose" so I installed that package (apt install
    docker.io docker-compose) and used nano (my preferred CLI editor) to create the yml file,
    doing a terminal copy and paste from the updated version I had locally. I then realized I also
    needed the migrate container to ensure the database was setup properly, so I boxed it up and
    pushed it to dockerhub. I then created the additional directories that would be needed as
    volumes (mkdir db and mkdir data) and used nano to create the environment files for the
    individual containers (.env.db, .env.rmq, .env.web, and .env.worker, example files included).
    I then switched to sftp to push the init.sql file to db and applicant_data.json file to data
    for the setup (mostly because I had forgotten this was an option for the other files).

    Assuming you're starting in the module_7 directory
    (
        sftp -i ~./.ssh/Module_7.pem ubuntu@23.20.142.10
        cd db
        lcd src/db
        put init.sql
        cd ../data
        lcd ../data
        put applicant_data.json
    )
    
    Halfway through the process my internet dropped out and I couldn't reconnect. I looked around
    at the EC2 settings and everything was running properly, then I remembered that we set it up
    for "My IP" which had likely changed with the reconnect. I went back in to the security
    settings and redid "My IP", it adjusted, and that fixed the problem.
    
    I then ran docker compose (docker compose -f docker-compose.ec2.yml up -d). The downloads went
    fine and everything started, but the worker errored out. After checking the docker output, I
    could see that the health check for RabbitMQ wasn't functioning as intended. RabbitMQ was
    posting messages after the web and worker were already running. Apparently RabbitMQ was still
    in the process of loading, even when the health check passed. I looked into it and found that
    the ping method (test: ["CMD-SHELL", "rabbitmq-diagnostics -q ping"]) can return a false
    positive. The port can be open, but the server may not be accepting connections yet. I adjusted
    the check to use check_port_connectivity with rabbitmq-diagnostics (test: ["CMD",
    "rabbitmq-diagnostics", "check_port_connectivity"]), and added a 10s start period to the health
    check (start_period: 10s). Additional TODO for the future if I have time is a connection retry
    attempt (limited to maybe 5 times with a short delay?) in the worker.

    Running docker compose again everything loaded properly and was up and running. I tried to
    connect to the server and I got nothing. Since I was getting no response at all, I figured the
    problem was in the security permissions, and I was correct. I had used port 80 instead of 8080.
    Easy fix and everything was good. All of the buttons functioned properly and refreshing gave
    the correct updated analysis. I took my screenshots, then closed out docker (docker compose
    -f docker-compose.ec2.yml down), went into AWS and shutdown the instance, and because AWS
    warned me I could still be charged for them holding the IP for the instance even when it wasn't
    running, I deleted the instance (cause I don't need to be paying Amazon for this and recreating
    it wouldn't be too difficult).
