-- What percentage of entries are from international students (not American or Other) (to two decimal places)?
SELECT
ROUND
    (
        (
            (
                SELECT CAST(COUNT(us_or_international) AS NUMERIC) FROM applicants WHERE us_or_international = 'International'
            )
/
            (
                SELECT CAST(COUNT(us_or_international) AS NUMERIC) FROM applicants
            )
        ) * 100, 2
    );