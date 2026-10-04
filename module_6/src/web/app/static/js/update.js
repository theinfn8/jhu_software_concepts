async function updateData()
{
    document.getElementById("status").innerText = "";
    const url = "./api/pull-data";
    try
    {
        const response = await fetch(url, {method: "POST"});
        if (!response.ok)
        {
            document.getElementById("status").innerText = "There was an error requesting the update: " + response.status;
            throw new Error(`Response status: ${response.status}`);
        }
        else
        {
            const result = await response.json();
            console.log(result);
            if (result.status == "queued")
            {
                document.getElementById("status").innerText = "Update has been queued";
            }
            else
            {
                document.getElementById("status").innerText = "Server returned an unknown response";
            }
        }
    }
    catch (error)
    {
        console.error(error.message);
    }
}

async function updateAnalysis()
{
    document.getElementById("status").innerText = "";
    const url = "./api/analysis";
    try
    {
        const response = await fetch(url, {method: "POST"});
        if (!response.ok)
        {
            document.getElementById("status").innerText = "There was an error requesting the update: " + response.status;
            throw new Error(`Response status: ${response.status}`);
        }
        else
        {
            const result = await response.json();
            console.log(result);
            if (result.status == "queued")
            {
                document.getElementById("status").innerText = "Analytics update queued!";
                
            }
            else
            {
                document.getElementById("status").innerText = "Server returned an unknown response";
            }
        }
    }
    catch (error)
    {
        console.error(error.message);
    }
}