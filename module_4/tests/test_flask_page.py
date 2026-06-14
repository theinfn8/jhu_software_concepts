import pytest

@pytest.mark.integration
@pytest.mark.web
def test_page_load(client,pg_connection,monkeypatch):
    # Only one page served from flask, buttons are API calls checked there

    # Point to DB test server
    def test_server(**conf):
        return pg_connection
    
    monkeypatch.setattr("psycopg.connect", test_server)
    response = client.get('/')
    assert response.status_code == 200
    assert b"<button onclick='updateAnalysis()'>Update Analysis</button>" in response.data
    assert b"<button onclick='updateData()'>Pull Data</button>" in response.data
    assert b"Analysis" in response.data