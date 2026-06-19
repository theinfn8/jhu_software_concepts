import pytest
import psycopg
from src.config import get_config

@pytest.mark.integration
def test_update(client,pg_connection, mock_new_data, monkeypatch):
    
    def get_config():
        return pg_connection

    monkeypatch.setattr("src.config.get_config", get_config())
    def mock_scrape(page):
        return mock_new_data

    monkeypatch.setattr("src.scrape.scrape_data", mock_scrape)
    try:
        response = client.post('/api/pull-data')
        assert response.status_code == 200
    except psycopg.Error as err:
        print(err)
        pytest.fail(err)
    