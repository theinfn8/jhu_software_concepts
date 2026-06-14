import pytest
from flask import Flask
import src.routes

@pytest.mark.web
def test_page_load(client,pg_connection,monkeypatch):
    response = client.get('/')
    assert response.status_code == 200
    assert b"<button onclick='updateAnalysis()'>Update Analysis</button>" in response.data
    assert b"<button onclick='updateData()'>Pull Data</button>" in response.data
    assert b"Analysis" in response.data

    def mock_empty_fetch(id):
        return None
    monkeypatch.setattr("src.scrape.scrape_data", mock_empty_fetch)
    response = client.post('/api/pull-data')
    assert response.status_code == 200

    def mock_full_fetch(id):
        return [{"id": 1, "program": "Environmental Economics", "university": "Stockholm University", "comments": "None", "date_added": "May 31, 2026", "url": "https://www.thegradcafe.com/result/1020288", "status": "Accepted", "status_date": "May 31", "accepted": "None", "rejected": "None", "term": "Fall 2026", "US/International": "International", "degree": "PhD", "gpa": "None", "gre": "None", "grev": "None", "greaw": "None", "llm-generated-program": "Environmental Economics", "llm-generated-university": "Stockholm University"}]
    def mock_insert(data):
        return None
    monkeypatch.setattr("src.scrape.scrape_data", mock_full_fetch)
    monkeypatch.setattr("src.load_data.insertEntries", mock_insert)
    response = client.post('/api/pull-data')
    assert response.status_code == 200

    # Point to test server
    def test_server(**conf):
        return pg_connection
    
    monkeypatch.setattr("psycopg.connect", test_server)
    response = client.get('/api/analysis')
    assert response.status_code == 200

    

