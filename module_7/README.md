Name: Chris Carson, ccarso12
Module Info: Module 7, Cloud Computing Assignment, Due Sunday by 23:59
How to Run:
    Create a domain in sagemaker that matches the domain of the S3 bucket.
    SageMaker Studio gives access to Jupyter notebooks on the left hand side near the bottom. Run
    Jupyter notebooks. Upload the ipynb or copy paste the code and run it.
    

Approach: 
    My approsch was again, a top down approach. Working through the directions was mostly
    straightforward. With the MFA, there were two places it gave me a green check mark, so I took
    a screenshot of both, just to be sure I got the one you were looking for.
    Figuring out the specific combination of permissions for my user account was a little trial and
    error. If I found there was a permission I needed that I had missed, I went back to IAM, found
    the one that would give the appropriate access, and added it.

    Creating the S3 bucket was pretty straightforward.

    SageMaker was the most complicated due to system issues, not code (as it turned out). SageMaker
    has been upgraded to SageMaker Studio, which required a lot of hoops to jump through to get the
    whole thing started, including adding additional permissions to the user account. Eventually, I
    was able to setup the domain and create the notebook. I found Jupyter still exists in the
    bottom left and started working there. I put in my download code and it didn't work. Role
    permission error. So I checked the roles assigned to the domain, checked that they had access,
    changed the code to try and force the role assumption. Anything I could think of. Eventually, I
    finally realized that the S3 Bucket was in the Stockholm region and the SageMaker instance was
    the N. Virginia region. Maybe because I am in Germany and Stockholm is closer? I started over,
    deleted the old S3 Bucket, recreated it in N. Virginia, uploaded the file and... it still
    didn't work, but my permissions error was a little different. I went to bed, came back,
    realized I hadn't updated the bucket name (changed it from -cdc to -cc) and the code worked.
    Since the code is Role based there are no secrets in the code. I did try and import the code
    from a s3_fetch.py file in the notebook, but it wouldn't import. I ran pylint on the s3_fetch
    code directly and on the ipynb. The only linting error I got was that the file name failed to
    conform to snake case, but I can't fix that, the filename was dictated by the assignment.

References: 
