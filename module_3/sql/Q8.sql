-- How many entries from 2026 are acceptances from applicants who applied to Georgetown University, MIT, Stanford University, or Carnegie Mellon University for a PhD in Computer Science?
-- Georgetown University, Massachusetts Institute of Technology, Stanford University, Carnegie Mellon University
-- Computer Science
SELECT COUNT(p_id)
FROM applicants
WHERE extract(YEAR FROM date_added) = 2026 AND
program LIKE '%Computer Science%' AND
university LIKE ANY (ARRAY['%Georgetown University%','%Massachusetts Institute of Technology%','%MIT%','%Stanford University%','%Carnegie Mellon%'])
