-- How many entries do you have in your database who have applied for Fall 2026?
SELECT COUNT(p_id)
FROM applicants
WHERE term = 'Fall 2026';