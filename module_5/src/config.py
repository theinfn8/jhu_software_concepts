"""
Database configuration loader.

This module provides a utility function for retrieving PostgreSQL
database connection parameters from environment variables. It supports
switching between production and test database configurations based on
the calling context.
"""

import os
from dotenv import load_dotenv

def get_config(testconfig=None):
    """Retrieve database connection configuration from environment variables.

    Reads database connection parameters (host, port, database name, user,
    and password) from environment variables. If ``testconfig`` is ``None``,
    production environment variables (prefixed with ``DB_``) are used.
    Otherwise, test environment variables (prefixed with ``TEST_DB_``) are
    used instead.

    :param testconfig: Flag indicating whether to load test configuration
        instead of production configuration. The value itself is not used;
        only whether it is ``None`` is checked. Defaults to ``None``.
    :type testconfig: any, optional
    :return: A dictionary containing the database connection parameters with
        keys ``"host"``, ``"port"``, ``"dbname"``, ``"user"``, and
        ``"password"``.
    :rtype: dict
    """

    load_dotenv()

    if testconfig is None:
        config = {
            "host" : os.getenv("host"),
            "port" : os.getenv("port"),
            "dbname" : os.getenv("dbname"),
            "user" : os.getenv("user"),
            "password" : os.getenv("password")
        }
    else:
        config = {
                "host" : os.getenv("host"),
                "port" : os.getenv("port"),
                "dbname" : os.getenv("dbname"),
                "user" : os.getenv("user"),
                "password" : os.getenv("password")
            }
    return config
