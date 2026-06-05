-- Do you numbers for question 8 change if you use LLM Generated Fields (rather than your downloaded fields)?
SELECT COUNT(p_id)
FROM applicants
WHERE extract(YEAR FROM date_added) = 2026 AND
program LIKE '%Computer Science%' AND
llm_generated_university LIKE ANY (ARRAY['%Georgetown University%','%Massachusetts Institute of Technology%','%MIT%','%Stanford University%','%Carnegie Mellon%'])