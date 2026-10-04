import pytest
import psycopg
from tests import test_config

@pytest.mark.integration
def test_update(client,pg_connection, mock_new_data, mock_old_data, monkeypatch):
     
    monkeypatch.setattr("src.config.config", test_config.config)
    def mock_scrape(page):
        return mock_new_data
    monkeypatch.setattr("src.scrape.scrape_data", mock_scrape)
    try:
        response = client.post('/api/pull-data')
        assert response.status_code == 200
    except psycopg.Error as err:
        print(err)
        pytest.fail(err)
    