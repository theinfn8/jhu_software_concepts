import pytest
import src.query_data as qd
import src.routes as routes
import re

percent_regex = re.compile(r"""^[0-9]+(\.[0-9]{1,2})?$""")

@pytest.mark.analysis
def test_getAnalysisHTML(pg_connection, monkeypatch):

    def test_server(**conf):
        return pg_connection
    
    monkeypatch.setattr("psycopg.connect", test_server)
    
    def simpleReturn(conn):
        return [0]
    
    def bigReturn(conn):
        return [0, 0, 0, 0]
    
    monkeypatch.setattr("src.query_data.getTermCount", simpleReturn)
    monkeypatch.setattr("src.query_data.getInternationalAverage", simpleReturn)
    monkeypatch.setattr("src.query_data.getAverageScores", bigReturn)
    monkeypatch.setattr("src.query_data.getAmericanGPA", simpleReturn)
    monkeypatch.setattr("src.query_data.getFallAcceptancesPercent", simpleReturn)
    monkeypatch.setattr("src.query_data.getFallAcceptancesGPA", simpleReturn)
    monkeypatch.setattr("src.query_data.getJHUCSEntries", simpleReturn)
    monkeypatch.setattr("src.query_data.getUniversityListAcceptances", simpleReturn)
    monkeypatch.setattr("src.query_data.getLLMUniversityListAcceptances", simpleReturn)
    monkeypatch.setattr("src.query_data.getBadGREAWScores", simpleReturn)
    monkeypatch.setattr("src.query_data.getBadGREScores", simpleReturn)

    resp = routes.getAnalysisHTML()
    # Need to verify answers are loaded from the api since the webpage calls this directly on load
    assert resp.count('Answer:') == 11


@pytest.mark.analysis
@pytest.mark.db
def test_getInternationalAverage(pg_connection):
    try:
        averagescores = str(qd.getInternationalAverage(pg_connection)[0])
        assert bool(percent_regex.search(averagescores))
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_getFallAcceptancesPercent(pg_connection):
    try:
        acceptanceAverage = str(qd.getFallAcceptancesPercent(pg_connection)[0])
        assert bool(percent_regex.search(acceptanceAverage))
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_getTermCount(pg_connection):
    try:
        assert qd.getTermCount(pg_connection)[0] > 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_getAverageScores(pg_connection):
    try:
        data = qd.getAverageScores(pg_connection)
        assert data[0] > 0
        assert data[1] > 0
        assert data[2] > 0
        assert data[3] > 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_getAmericanGPA(pg_connection):
    try:
        assert qd.getAmericanGPA(pg_connection)[0] > 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_getFallAcceptancesGPA(pg_connection):
    try:
        assert qd.getFallAcceptancesGPA(pg_connection)[0] > 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_getJHUCSEntries(pg_connection):
    try:
        assert qd.getJHUCSEntries(pg_connection)[0] >= 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_getUniversityListAcceptances(pg_connection):
    try:
        assert qd.getUniversityListAcceptances(pg_connection)[0] >= 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_getLLMUniversityListAcceptances(pg_connection):
    try:
        assert qd.getLLMUniversityListAcceptances(pg_connection)[0] >= 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_getBadGREAWScores(pg_connection):
    try:
        assert qd.getBadGREAWScores(pg_connection)[0] >= 0
    except:
        pytest.fail("Error raised")

@pytest.mark.db
@pytest.mark.analysis
def test_getBadGREScores(pg_connection):
    try:
        assert qd.getBadGREScores(pg_connection)[0] >= 0
    except:
        pytest.fail("Error raised")

@pytest.mark.analysis
def test_getStats():
    qd.getStats();