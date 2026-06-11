import pytest
import requests
from flask import Flask

from src.app import create_app

@pytest.fixture()
def flask_app():
    flask_app = create_app()
    flask_app.config.update({'TESTING': True})
    yield flask_app

@pytest.fixture()
def client(flask_app):
    return flask_app.test_client()

@pytest.fixture()
def runner(flask_app):
    return flask_app.test_cli_runner()

@pytest.fixture(autouse=True)
def disable_network_calls(monkeypatch):
    def stunted_get():
        raise RuntimeError("Network access not allowed during testing!")
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: stunted_get())