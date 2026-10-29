const POLL_INTERVAL_MS = 2000;

function setStatus(text)
{
    document.getElementById("status").innerText = text;
}

function setButtonsDisabled(disabled)
{
    document.getElementById("update-data").disabled = disabled;
    document.getElementById("update-analysis").disabled = disabled;
}

// Poll a task until the worker finishes it; resolves with the final task record
async function pollTask(taskId, label)
{
    while (true)
    {
        const response = await fetch("./api/tasks/" + taskId);
        if (!response.ok)
        {
            throw new Error(`Task status request failed: ${response.status}`);
        }
        const task = await response.json();
        if (task.status == "succeeded" || task.status == "failed")
        {
            return task;
        }
        if (task.stale)
        {
            task.status = "failed";
            task.error = "Task has not finished, the worker may have stopped";
            return task;
        }
        setStatus(label + " " + task.status + "...");
        await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL_MS));
    }
}

async function refreshAnalysis()
{
    const response = await fetch("./api/analysis");
    if (!response.ok)
    {
        throw new Error(`Analysis request failed: ${response.status}`);
    }
    const result = await response.json();
    document.getElementById("analysis").innerHTML = result.content;
}

// Queue a task, wait for the worker to finish it, then run onSuccess
async function runTask(url, label, onSuccess)
{
    setStatus("");
    setButtonsDisabled(true);
    try
    {
        const response = await fetch(url, {method: "POST"});
        if (!response.ok)
        {
            throw new Error("There was an error requesting the update: " + response.status);
        }
        const result = await response.json();
        console.log(result);
        if (result.status != "queued")
        {
            setStatus("Server returned an unknown response");
            return;
        }
        setStatus(label + " queued...");
        const task = await pollTask(result.task_id, label);
        if (task.status == "succeeded")
        {
            await onSuccess();
            setStatus(label + " complete");
        }
        else
        {
            setStatus(label + " failed: " + task.error);
        }
    }
    catch (error)
    {
        console.error(error.message);
        setStatus(error.message);
    }
    finally
    {
        setButtonsDisabled(false);
    }
}

async function updateData()
{
    await runTask("./api/pull-data", "Data pull", async () => {});
}

async function updateAnalysis()
{
    await runTask("./api/analysis", "Analysis update", refreshAnalysis);
}
