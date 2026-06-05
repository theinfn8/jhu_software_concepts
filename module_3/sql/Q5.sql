-- What percent of entries for Fall 2026 are Acceptances (to two decimal places)?
SELECT
ROUND
    (
        (
            (
                SELECT CAST(COUNT(p_id) AS NUMERIC) FROM applicants WHERE status = 'Accepted'
            )
/
            (
                SELECT CAST(COUNT(p_id) AS NUMERIC) FROM applicants
            )
        ) * 100, 2
    );