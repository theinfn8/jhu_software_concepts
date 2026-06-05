CREATE TABLE IF NOT EXISTS applicants (
    p_id integer PRIMARY KEY,
    program text,
    university text,
    comments text,
    date_added date,
    url text,
    status text,
    term text,
    us_or_international text,
    gpa float,
    gre float,
    gre_v float,
    gre_aw float,
    degree text,
    llm_generated_program text,
    llm_generated_university text
);
