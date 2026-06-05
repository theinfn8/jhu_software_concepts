-- How many applicants reported GRE AW scores higher than the maximum?
SELECT COUNT(p_id)
FROM applicants
WHERE gre_aw > 6