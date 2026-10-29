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

--
-- Name: tasks; Type: TABLE; Schema: public; Owner: grad_admin
--

CREATE TABLE public.tasks (
    task_id uuid NOT NULL,
    kind text NOT NULL,
    status text DEFAULT 'queued' NOT NULL,
    error text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT tasks_status_check CHECK (status IN ('queued', 'running', 'succeeded', 'failed'))
);

--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: grad_admin
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (task_id);
