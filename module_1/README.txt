1 Getting Started:
1.1 From the root "module_1" directory, activate the virtual environment (for me, source mod1_env/bin/activate)
1.2 From the root "module_1" directory, use python to run run.py (for me, python3 run.py)

2 References:
2.1 The 404 for the favicon was bugging my programmer brain, so I looked it up. Solution was simple,
    serve the favicon directly. Used this site:
    https://flask.palletsprojects.com/en/stable/patterns/favicon/

2.2 Serving static pages for every page seemed redundant and counter to templating concepts. Looked
    up a little on the templating engine and actually templated the site. Used this site for info:
    https://www.digitalocean.com/community/tutorials/how-to-use-templates-in-a-flask-application

2.3 Switching to a blueprint caused some issues, used the following site as a basis but ultimately
    I had to work out my own structural differences that were causing problems. It was generally
    useful (as most Digital Ocean tutorials are), but didn't really give a full solution.
    https://www.digitalocean.com/community/tutorials/how-to-structure-a-large-flask-application-with-flask-blueprints-and-flask-sqlalchemy

2.4 Referenced a book already in my collection for general setup: Mastering Flask Web and API
    Development.
    Tragura, S.J.C (2024, August) Mastering Flask Web and API Development, Packt Publishing
