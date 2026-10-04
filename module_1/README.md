## __Module 1__

### __Name__: Chris Carson, ccarso12\
### __Module Info__: Module 1, Scale and LM Deployment Assignment, Due 8 Aug 2026\

### __Installation and Running__:\
Create a virtual environment and activate it\
```python3 -m venv venv```
```activate venv/bin/activate```
Install the requirements from requirements.txt\
```pip install -r requirements.txt```
Use python to run run.py\
```python3 run.py```
In a browser, navigate to either http://localhost:8080 or http://127.0.0.1:8080\ to view the site

### __Expected Outputs__:
The website should be a simple about me site with futures links to projects.

### __Approach__:
Straightforward website. Serving static pages for every page seemed redundant and counter to templating concepts. Looked
up a little on the templating engine and actually templated the site. Switching to a blueprint caused some issues, used the following site as a basis but ultimately I had to work out my own structural differences that were causing problems.
