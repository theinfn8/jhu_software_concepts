import pytest
from threading import Lock
from flask import Flask

from src.app import create_app


@pytest.mark.buttons
def test_updateDatabase(client, pg_connection, disable_network_calls, monkeypatch):
    # Fake a successful pull with no new records found
    def mock_fetch(id):
        return None
    # Just checking functionality here, don't want an actual DB write at this stage
    def mock_insert(data):
        return None
    monkeypatch.setattr("src.scrape.scrape_data", mock_fetch)
    monkeypatch.setattr("src.load_data.insert_entries", mock_insert)
    response = client.post('/api/pull-data')
    assert response.status_code == 200

    # Mock fake scraped records return
    def mock_full_fetch(id):
        return [{"id": 1, "program": "Environmental Economics", "university": "Stockholm University", "comments": "None", "date_added": "May 31, 2026", "url": "https://www.thegradcafe.com/result/1020288", "status": "Accepted", "status_date": "May 31", "accepted": "None", "rejected": "None", "term": "Fall 2026", "US/International": "International", "degree": "PhD", "gpa": "None", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Environmental Economics", "llm-generated-university": "Stockholm University"}]
    monkeypatch.setattr("src.scrape.scrape_data", mock_full_fetch)
    response = client.post('/api/pull-data')
    assert response.status_code == 200

    UPDATING_LOCK = Lock()
    UPDATING_LOCK.acquire()
    monkeypatch.setattr("src.routes.UPDATING_LOCK", UPDATING_LOCK)
    response2 = client.post('/api/pull-data')
    assert response2.status_code == 409
    UPDATING_LOCK.release()

@pytest.mark.buttons
def test_update_analysis(client, pg_connection, monkeypatch):

    # Point to DB test server
    def test_server(**conf):
        return pg_connection
    
    monkeypatch.setattr("psycopg.connect", test_server)
    response = client.get('/api/analysis')
    assert response.status_code == 200
    assert b"Answer:" in response.data

    UPDATING_LOCK = Lock()
    UPDATING_LOCK.acquire()
    monkeypatch.setattr("src.routes.UPDATING_LOCK", UPDATING_LOCK)
    response = client.get('/api/analysis')
    assert response.status_code == 409
    UPDATING_LOCK.release
