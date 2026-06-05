-- What is the average GPA of applicants who applied for Fall 2026 who are Acceptances?
SELECT AVG(gpa)
FROM applicants
WHERE term = 'Fall 2026' AND gpa > 0;