Name: Chris Carson, ccarso12
Module Info: Module 2, Web Scraping, Due Sunday by 23:59
Approach: I started the process by examining the publicly available pages by hand to get a feel for
    what kind of data would be available. I then checked the robots.txt file to see if there were
    any limitations on what pages could be scraped. I identified two options for the necessary
    data, iterating through "result" pages (probably in decreasing order until I had my needed
    quantity) or parsing the data from the "survey" table, one page at a time. Neither of these are
    listed as restricted pages.

    The survey method seemed like it would get 20 entries per html fetch but would be a little more
    complicated. To reduce quantity of hits against the server, I opted for this route. I then
    examined the source of the page and identified there was one tbody and that there was a
    consistent order to the data within each tr. Picking apart the html from there made it easy to
    identify what pieces I would need and that Selenium would not be necessary (the pagination is
    within the URL) and would only need urllib3 and BeautifulSoup.

    I started with building a sample pull that pulled and parsed the first entry and created a temp
    dictionary creation method that autofilled with a default "None" to ensure all fields were
    filled. Once that worked I moved the BeautifulSoup traversal of the rows into their own
    functions for clarity. Then added a loop to select all 20 entries and add the entries to a
    list. Then I added a second loop to iterate the pages for the quantity that I would need and
    added the json export of the list (to get a json file similar to the example). Finally I moved
    the test pieces into their final locations for structure, and saved out the tbody from each
    page scraped to source_html.json, so I would have the original HTML to fallback to if needed.

    After scraping 50,000 records, I made a couple adjustments to the base settings of the LLM.
    Hand set the cores so it wouldn't pin all of my CPUs to 100% (only half of them) and set it to
    offload 32 layers to the GPU (I have a pretty powerful GPU with a lot of VRAM, but it didn't
    seem to work). Even with this the LLM was incredibly slow. Validation checking is showing
    completely random llm-generated-universities and some programs with bad name changes. For
    example, in the very first entry, the university scraped was "Stockholm University" and the
    llm-generated-university was "University of British Columbia".
    
    I think it might be related to none of my programs containing a "program, university" pair. I
    scraped each individually from the HTML. I have little experience working with LLMs and that
    is my best guess.