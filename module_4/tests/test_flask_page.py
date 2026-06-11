import pytest
from flask import Flask

@pytest.mark.web
def test_page_load(client,monkeypatch):
    response = client.get('/')
    assert response.status_code == 200
    assert b"<button onclick='updateAnalysis()'>Update Analysis</button>" in response.data
    assert b"<button onclick='updateData()'>Pull Data</button>" in response.data
    assert b"Analysis" in response.data

    def mock_fetch(id):
        return None
    monkeypatch.setattr("src.scrape.scrape_data", mock_fetch)

    response = client.get('/api/analysis')
    assert response.status_code == 200
    # Need to verify answers are loaded from the api since the webpage calls this directly on load
    assert b"Answer:" in response.data
    response = client.post('/api/pull-data')
    assert response.status_code == 200

