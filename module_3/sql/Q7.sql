-- How many entries are from applicants who applied to JHU for a masters degrees in Computer Science?
SELECT count(p_id)
FROM applicants
WHERE program LIKE '%Computer Science%' AND university LIKE '%Johns Hopkins%';