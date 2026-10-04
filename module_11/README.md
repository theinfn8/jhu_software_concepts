## __Module 10__

### __Name__: Chris Carson, ccarso12\
### __Module Info__: Module 11, MLOps Pipeline, Due Sunday by 23:59\
### __Installation and Running__:\
Create a virtual environment and activate it\
```python3 -m venv venv```
Install the requirements from requirements.txt\
```pip install -r requirements.txt```
Place the gradcafe data file in the same location as the python files. It expects a JSON file
in the format of 'cleaned_gradcafe.json'.\
Run MLFlow first, ```'mlflow server --host 127.0.0.1 --port 8080'```\
Run the kmeans second, ```python kmeans_mlops_pipeline```\
The MLFlow dashboard can then be reached in a browser at http://localhost:8080 or http://127.0.0.1:8080

### __Expected Outputs__:
kmeans_mlops_pipeline will information to indicate where it is in the process of the kmeans and some useful information on the logging process.

### __Approach__:
I started this by cleaning up the GRE data. I copied all gre scores that were in the combined gre score range and copied them to a new column gre_combined, then selected all gre scores in the dataset that: were in the combined range and also possessed a valid gre_v score. I then replaced the score in gre with the difference (logically, the GRE Quant score). Since I did this in AWS, I just re-ran the whole thing to get a new cleaned dataset and downloaded it for this assignment.

I copied the module 9 code over and started looking at the requirements and what needed to stay and what needed to go. I removed anything dealing with the University, since it was never used in generating the kmeans model in the previous assignment and was just added noise here. Likewise, I removed the plotting functions as additional unnecessary code (which was thankfully easy because I split the code for this into their own functions). Which included the GRE portion of that assignment. I had a hard time deciding if I needed the elbow estimation, since the parameters were already set by the rubric. In the end, I decided to keep the code in and calculate the elbow, but the program does nothing with it (effectively useless code, but it felt like it was an important part of module 9 and the model creation that I would be removing).

With the restructure complete, I added the connection to MLFlow and added the MLFlow run code. Then I fired up MLFlow, ran the pipeline, and checked everything worked properly. Took screenshots as required. I felt like the process should have been more complicated, but maybe that speaks to the maturity of MLFlow and its Python implementation.
