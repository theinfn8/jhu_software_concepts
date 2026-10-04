## __Module 13__

### __Name__: Chris Carson, ccarso12\
### __Module Info__: Module 13, Scale and LM Deployment Assignment, Due 8 Aug 2026\

### __Files__:
./
├── Blank_Form.png
├── data
│   └── cleaned_gradcafe.json
├── inference.py
├── Prediction.png
├── README.md
├── requirements-rocm.txt
├── requirements.txt
├── run.py
├── saved_model
│   ├── config.json
│   ├── metadata.json
│   ├── model.safetensors
│   ├── tokenizer_config.json
│   └── tokenizer.json
├── src
│   ├── app.py
│   ├── clean.py
│   ├── config.py
│   ├── .env.example
│   ├── __init__.py
│   ├── load_data.py
│   ├── predictor.py
│   ├── query_data.py
│   ├── routes.py
│   ├── scrape.py
│   ├── static
│   │   ├── css
│   │   │   └── main.css
│   │   ├── favicon.ico
│   │   └── js
│   │       ├── predict.js
│   │       └── update.js
│   └── templates
│       ├── base.html
│       ├── index.html
│       └── predict.html
├── Training_Eval.png
├── training_log.txt
├── train_model.py
├── tree.txt
└── writeup.pdf

### __Installation and Running__:\
Create a virtual environment and activate it\
```python3 -m venv venv```
```activate venv/bin/activate```
Install the requirements from requirements.txt\
```pip install -r requirements.txt```
(If you happen to have the specific AMD ROCm family I have, GFX1030, then you can use requirements-rocm.txt instead to get GPU support)
Since this is based on Module 5, the .env needs to be in the src directory with the rest of the flask app, example is .env.example
Run the training module: ```python3 train_model.py```\
With GPU, expect about 30 minutes of run time. With CPU only, expect much longer times.\
Make sure the .env file is updated\
* If there is a postgresql database running with an applicants table and data that matches the Module 5 schema, just running the flask app will work. If you are only interested in whether the prediction portion works, it will still run even without the postgresql database.\
```python3 run.py```\
* If there is an empty postgresql server that is referenced from the .env, then it can be filled before hand (assuming the account has rights to create the table).\
```python3 run.py --setup```\
In a browser, navigate to either http://localhost:8080 or http://127.0.0.1:8080\
The page defaults to the analysis, the new prediction page is linked in the top right. After submitting form data the page gives the prediction at the top, with the form ready to go for another round.\

### __Expected Outputs__:
The train_model program runs all of the initial build steps in order. It prints progress indicators throughout the process, including the analysis at the relevant parts. It is a lot of output, so I included a copy of my output in 'training_log.txt' for quicker reference.\
The website is the same layout as the original Module 5, but I added links at the top right for the analysis page and the prediction page. The prediciton page gives the warning up front at the top of the page, with the form below. I added a front-end check for some simple data validity for normal users, and a back-end check for those trying to circumvent the system. The prediction appears at the top of the page with the prediction and the score (as a percentage).

### __Approach__:
I followed this again mostly in order, step for step. I like to plan first, so as always, I took a look at the data I was working with and did a survey of the comments to get a feel for what I was looking at (I hadn't really considered them previously.) I then settled on the fields that I would use. I opted to exclude the 'term' data, as I wasn't sure that it would play a large part in the decision (or that it might not skew the prediction). I settled on a format for the inject to the model. I then proceeded to do the required clean up and prep (training split, et al).

I then did a little research on the model options. Short answer, I chose the recommended model/tokenizer with the recommended baseline configuration, since it seemed the most appropriate. More info on why exactly in the analysis/writeup. Moved to the training pipeline itself. I ran into a little snag here, when I didn't get even the first iteration of the training feedback to return after about 10 minutes. Apparently, because I run an AMD card that needs ROCm to run with PyTorch, it doesn't automatically use the GPU. I had to isolate my specific card family, then locate a version that was designed to work with that specific family. Long story short, I made a second requirements file that downloads the specific version I need for my very specific setup but left the normal requirements.txt for anyone else. Which brought the training pipeline down to a reasonable ~30 minutes.

Afterward, I wrote up the final evaluation code, and then the save and reload portions. I tried to split out some of these functions to be able to only need to write it once and employ parts in inference.py. I ran the whole thing to make sure I had end-to-end completion, then ran it again to redirect the output into the log file. Once completed, I created inference.py and moved to the flask portion of the assignment.


When looking at the Module options for the basis of the Flask app, I went with the recommended Module 5. I decided to incorporate the comments from the assignment feedback in line with the course final. I cleaned up the code, added more robust error checking, and then... discovered that the week or so downtime from Grad Cafe was them implementing a cursor re-write for the listing page that completely broke my scraping code. On the bright side, once I identified the error the fix was relatively easy, shifting from a pagination based system to moving the cursor. Down side, all of my old scrape code in all of the other modules is now broken as well and will need to be updated to continue to work.

Once the module 5 code was squared away, I added the prediction page. Thankfully, it worked as planned. I tried to make the back-end more robust dealing with user entries and error handling. Knowing that the industry standard is to check data inputs twice, I made some javascript checks for the front-end and then double check the data once received on the back-end (one can be considered a user friendliness issue, the other a data security issue). Everything still seemed good, so I tweaked everything to my satisfaction. Then I realised that there might not be a database to back the analysis part of the website. I added a setup command line flag that would import the data to the database (I was still using my original docker database from module... 3?). As stated above, if there is a database that has the Module 5 schema table already installed, it will run with whatever is in it. If there isn't, the setup will need to be run to populate the database with the table and data. If you aren't interested in that portion of the site, you can not even run the postgresql server and the site will still serve and function for the "Will You Get In?" portion of the site.

I then started the write-up.

### __Analysis__:

Write up for this is incredibly long, and can be found in writeup.pdf.

### __References__:
Fenner, M. E. (2020). Machine learning with Python for everyone. Pearson Education, Inc.
