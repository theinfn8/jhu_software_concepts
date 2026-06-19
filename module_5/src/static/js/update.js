async function updateData()
{
    document.getElementById("status").innerText = "Update in progress";
    const url = "./api/pull-data";
    try
    {
        const response = await fetch(url, {method: "POST"});
        if (response.status == 409)
        {
            document.getElementById("status").innerText = "Data update already in progress";
        }
        else if (!response.ok)
        {
            document.getElementById("status").innerText = "There was an error requesting the update: " + response.status;
            throw new Error(`Response status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log(result);
        if (result.status == "Available")
        {
            document.getElementById("status").innerText = "Update is available";
        }
        else
        {
            document.getElementById("status").innerText = "Update in progress";
        }
    }
    catch (error)
    {
        console.error(error.message);
    }
}

async function updateAnalysis()
{
    document.getElementById("status").innerText = "Analysis update in progress";
    const url = "./api/analysis";
    try
    {
        const response = await fetch(url);
        if (response.status == 409)
        {
            document.getElementById("status").innerText = "Can't recalculate analysis, data update in progress";
        }
        else if (!response.ok)
        {
            document.getElementById("status").innerText = "There was an error requesting the update: " + response.status;
            throw new Error(`Response status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log(result);
        if (result.status == "Available")
        {
            document.getElementById("status").innerText = "Analysis updated!";
            document.getElementById("analysis").innerHTML = result.content;
        }
        else
        {
            document.getElementById("status").innerText = "Can't recalculate analysis, data update in progress";
        }
    }
    catch (error)
    {
        console.error(error.message);
    }
}