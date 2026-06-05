-- What is their average GPA of American students in Fall 2026?
SELECT AVG(gpa)
    FROM applicants
    WHERE us_or_international = 'American'