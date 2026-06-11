import pytest
from flask import Flask
import src.load_data

from src.app import create_app, setUpdate


@pytest.mark.web
def test_updateDatabase(client, monkeypatch):
    response = client.post('/api/pull-data')
    assert response.status_code == 200

    def mock_fetch():
        return None
    
    monkeypatch.setattr("src.app.updating", True)
    monkeypatch.setattr("src.scrape.scrape_data", mock_fetch)
    response2 = client.post('/api/pull-data')
    assert response2.status_code == 409

@pytest.mark.web
def test_insertEntries(client, monkeypatch):
    response = client.get('/api/analysis')
    assert response.status_code == 200

    monkeypatch.setattr("src.app.updating", True)
    response = client.get('/api/analysis')
    assert response.status_code == 409
