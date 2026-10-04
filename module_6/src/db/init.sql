--
-- Roles
--

--
-- User Configurations
--

-- Create user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grad_user') THEN
        CREATE USER grad_user
            WITH PASSWORD 'grad_user_pass'
            NOSUPERUSER     -- cannot perform superuser operations
            NOCREATEDB      -- cannot create databases
            NOCREATEROLE    -- cannot create roles or users
            NOINHERIT       -- does not inherit privileges of roles it is a member of
            LOGIN;          -- can log in
    END IF;
END $$;



--
-- Name: applicants; Type: TABLE; Schema: public; Owner: grad_admin
--

CREATE TABLE public.applicants (
    p_id integer NOT NULL,
    program text,
    degree text,
    university text,
    comments text,
    date_added date,
    url text,
    status text,
    term text,
    us_or_international text,
    gpa double precision,
    gre double precision,
    gre_v double precision,
    gre_aw double precision,
    llm_generated_program text,
    llm_generated_university text
);


--
-- Name: ingestion_watermarks; Type: TABLE; Schema: public; Owner: grad_admin
--

CREATE TABLE public.ingestion_watermarks (
    source text NOT NULL,
    last_seen integer,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: applicants applicants_pkey; Type: CONSTRAINT; Schema: public; Owner: grad_admin
--

ALTER TABLE ONLY public.applicants
    ADD CONSTRAINT applicants_pkey PRIMARY KEY (p_id);

--
-- Name: ingestion_watermarks ingestion_watermarks_pkey; Type: CONSTRAINT; Schema: public; Owner: grad_admin
--

ALTER TABLE ONLY public.ingestion_watermarks
    ADD CONSTRAINT ingestion_watermarks_pkey PRIMARY KEY (source);
