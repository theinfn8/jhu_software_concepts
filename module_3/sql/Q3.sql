-- What is the average GPA, GRE, GRE V, GRE AW of applicants who provide these metrics?
SELECT
    (SELECT AVG(gpa) FROM applicants WHERE gpa > 0) AS avg_gpa,
    (SELECT AVG(gre) FROM applicants WHERE gre > 0) AS avg_gre,
    (SELECT AVG(gre_v) FROM applicants WHERE gre_v > 0) AS avg_gre_v,
    (SELECT AVG(gre_aw) FROM applicants WHERE gre_aw >= 0) AS avg_gre_aw