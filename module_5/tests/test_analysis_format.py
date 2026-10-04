import pytest
import src.query_data as qd
import src.routes as routes
import re

percent_regex = re.compile(r"""^[0-9]+(\.[0-9]{1,2})?$""")

@pytest.mark.analysis
def test_get_analysis_html(pg_connection, monkeypatch):

    def test_server(**conf):
        return pg_connection
    
    monkeypatch.setattr("psycopg.connect", test_server)
    
    def simpleReturn(conn):
        return [0]
    
    def bigReturn(conn):
        return [0, 0, 0, 0]
    
    monkeypatch.setattr("src.query_data.get_term_count", simpleReturn)
    monkeypatch.setattr("src.query_data.get_international_average", simpleReturn)
    monkeypatch.setattr("src.query_data.get_average_scores", bigReturn)
    monkeypatch.setattr("src.query_data.get_american_gpa", simpleReturn)
    monkeypatch.setattr("src.query_data.get_fall_acceptance_percent", simpleReturn)
    monkeypatch.setattr("src.query_data.get_fall_acceptance_gpa", simpleReturn)
    monkeypatch.setattr("src.query_data.get_jhu_cs_entries", simpleReturn)
    monkeypatch.setattr("src.query_data.get_uni_acceptances", simpleReturn)
    monkeypatch.setattr("src.query_data.get_llm_uni_acceptances", simpleReturn)
    monkeypatch.setattr("src.query_data.get_bad_gre_aw_scores", simpleReturn)
    monkeypatch.setattr("src.query_data.get_bad_gre_scores", simpleReturn)

    resp = routes.get_analysis_html()
    # Need to verify answers are loaded from the api since the webpage calls this directly on load
    assert resp.count('Answer:') == 11


@pytest.mark.analysis
@pytest.mark.db
def test_get_international_average(pg_connection):
    try:
        averagescores = str(qd.get_international_average(pg_connection)[0])
        assert bool(percent_regex.search(averagescores))
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_get_fall_acceptance_percent(pg_connection):
    try:
        acceptanceAverage = str(qd.get_fall_acceptance_percent(pg_connection)[0])
        assert bool(percent_regex.search(acceptanceAverage))
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_get_term_count(pg_connection):
    try:
        assert qd.get_term_count(pg_connection)[0] > 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_get_average_scores(pg_connection):
    try:
        data = qd.get_average_scores(pg_connection)
        assert data[0] > 0
        assert data[1] > 0
        assert data[2] > 0
        assert data[3] > 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_get_american_gpa(pg_connection):
    try:
        assert qd.get_american_gpa(pg_connection)[0] > 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_get_fall_acceptance_gpa(pg_connection):
    try:
        assert qd.get_fall_acceptance_gpa(pg_connection)[0] > 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_get_jhu_cs_entries(pg_connection):
    try:
        assert qd.get_jhu_cs_entries(pg_connection)[0] >= 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_get_uni_acceptances(pg_connection):
    try:
        assert qd.get_uni_acceptances(pg_connection)[0] >= 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_get_llm_uni_acceptances(pg_connection):
    try:
        assert qd.get_llm_uni_acceptances(pg_connection)[0] >= 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_get_bad_gre_aw_scores(pg_connection):
    try:
        assert qd.get_bad_gre_aw_scores(pg_connection)[0] >= 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_get_bad_gre_scores(pg_connection):
    try:
        assert qd.get_bad_gre_scores(pg_connection)[0] >= 0
    except:
        pytest.fail("Error raised")

@pytest.mark.analysis
def test_get_stats():
    qd.get_stats();