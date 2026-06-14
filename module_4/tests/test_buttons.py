import pytest
from flask import Flask

from src.app import create_app


@pytest.mark.web
def test_updateDatabase(client, disable_network_calls, monkeypatch):
    # Fake a successful pull with no new records found
    def mock_fetch(id):
        return None
    monkeypatch.setattr("src.scrape.scrape_data", mock_fetch)
    response = client.post('/api/pull-data')
    assert response.status_code == 200

    monkeypatch.setattr("src.routes.updating", True)
    response2 = client.post('/api/pull-data')
    assert response2.status_code == 409

@pytest.mark.web
def test_updateAnalysis(client, monkeypatch):
    response = client.get('/api/analysis')
    assert response.status_code == 200
    assert b"Answer:" in response.data

    monkeypatch.setattr("src.routes.updating", True)
    response = client.get('/api/analysis')
    assert response.status_code == 409
