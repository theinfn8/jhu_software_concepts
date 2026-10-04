Name: Chris Carson, ccarso12
Module Info: Module 8, Data Preparation & Models Assignment, Due Monday by 23:59
Installation and Running:
    Create a virtual environment and activate it
    Install the requirements from requirements.txt
    Place the gradcafe data file in the same location as the python file. It expects the
    "cleaned_gradcafe.json" file.
    Run with python

Expected Outputs:
    The program should create all of the PNGs requested in the assignment over the course of its
    run. In addition, it will generate a table PNG for the 100 lines of cluster data. Along the
    process, it will provide some feedback regarding what step it is on. The application of the
    model takes a bit of time as it runs through about 100 possibile clusterings. The final piece
    of the code will give my thoughts on the boxplots and the GRE data.

Approach:
    I took the feedback from the last module and went back and corrected the issues that were
    identified in the data and re-generated the cleaned_gradcafe.json file.

    I mostly worked this in the same top down fashion, and split the task into basically three
    related sections. Basic loading/startup, the modeling pipeline, and the analysis. I tried to
    identify sections of code that would benefit from a more generalized function, rather than just
    repeat code over and over again. I also attempted to keep chart creation code in its own
    function calls, since charts are mostly just code related to setup and can clutter the main
    logic.

    After writing the initial framework, I did yet another pass and ended up consolidating more
    code. I also took a look at the charts and made some adjustments (the cluster list had a bad
    title that needed to be adjusted due to the size of the list).
    
    While looking at the elbow chart, it occured to me (at least with this data), that there was
    likely a way to automate the detection of the elbow. Since the curve was a nice smooth curve, I
    decided to fit an equation to the line, then use the "velocity" and "acceleration" (derivative
    and second derivative) to identify where the curve has, crossed a threshold, shall we say. This
    gives me a solid mathematics based estimate of the best number of clusters (which,
    interestingly, at 71 was also very close to the estimate from the assignment). I added the
    estimate line to the elbow chart for reference and updated the documentation to explain the
    process a little more.

    Originally, I did the cluster size selection as a step 5 to sped up the process, but with the
    switch to the calculus-based estimation it makes more sense to have the finer granularity. The
    math itself is pretty fast though.
    
    For the cluster selection, I did a keyword-based check to try and identify the cluster that was
    associated with the degree programs we were looking for. Then ran with those clusters. I
    compared them visually and added my thoughts on the data into the program and will include it
    here because I wasn't sure where the analysis should go.

Analysis:
    Analysis of the GRE data for the two clusters seems to be a reasonable spread.
    Both clusters demonstrate the "GRE total" vs "GRE-Q only" problem that I identified
    earlier. Both plots also show that there are still some items within the data that are
    out of bounds for our expected return (an item in the 600 range, for example).
    Data cleaning would need to drop the invalid scores, if there is a valid GRE V, then
    it would be possible to figure out the GRE Q score from the combined score. Otherwise,
    it might be necessary to divide the column data into two separate columns, one for
    combined, one for GRE Q.

References: 
    Tuckfield, B. (2023). Dive into data science: Use Python to tackle your toughest business
    challenges. No Starch Press.

    Morley, S. (2020). Applying math with Python: Practical recipes for solving computational math problems using Python programming and its libraries. Packt Publishing.

    Garrido, J. M. (2016). Introduction to computational models with Python. CRC Press.