"""
Entry point for the GradCafe Analytics Flask app.

Normally just creates and runs the Flask app. Pass ``--setup`` to also
ensure the ``applicants`` table exists and is populated from a cleaned
JSON export (see :func:`src.load_data.load_json_into_database`) before
the app starts -- useful for a fresh database, or to re-run the bulk
load safely (it's idempotent; existing rows are left untouched).

**Usage:**

.. code-block:: bash

    # Normal run, no setup step
    python3 run.py

    # Ensure the table exists and is loaded from the default JSON path
    # (data/cleaned_gradcafe.json) before starting the app
    python3 run.py --setup

    # Same, but load from a different JSON export
    python3 run.py --setup --data-path path/to/other_export.json
"""

import argparse
import sys

import psycopg

from src.app import create_app
from src import load_data

DEFAULT_JSON_PATH = "data/cleaned_gradcafe.json"

def parse_args():
    """
    Parse command-line arguments for this entry point.

    :returns: The parsed arguments, with ``setup`` (bool) and
        ``data_path`` (str) attributes.
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="Run the GradCafe Analytics Flask app."
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help=(
            "Create the applicants table if it doesn't already exist, "
            "and bulk-load it from a cleaned JSON export, before "
            "starting the Flask app. Safe to re-run -- existing rows "
            "(matched by p_id) are left untouched, not duplicated."
        ),
    )
    parser.add_argument(
        "--data-path",
        default=DEFAULT_JSON_PATH,
        help=(
            "Path to the cleaned JSON export to load when --setup is "
            f"given (default: {DEFAULT_JSON_PATH})."
        ),
    )
    return parser.parse_args()

def run_setup(data_path):
    """
    Create the ``applicants`` table if missing and bulk-load ``data_path``.

    Thin wrapper around :func:`src.load_data.load_json_into_database`
    that reports progress and turns the most common failure modes
    (missing file, unreachable database) into a clear, single-line
    message and a non-zero exit rather than a raw traceback, since this
    runs before the Flask app (and its own error handling) even starts.

    :param data_path: Path to the cleaned JSON export to load.
    :type data_path: str
    :returns: None. Exits the process with status ``1`` on failure.
    :rtype: None
    """
    print(f"Running database setup from '{data_path}' ...")
    try:
        count = load_data.load_json_into_database(data_path)
    except FileNotFoundError:
        print(f"Setup failed: no file found at '{data_path}'.")
        sys.exit(1)
    except psycopg.Error as exc:
        print(f"Setup failed: could not reach the database ({exc}).")
        sys.exit(1)

    print(f"Database setup complete: {count} records processed from '{data_path}'.")

if __name__=='__main__':
    args = parse_args()

    if args.setup:
        run_setup(args.data_path)

    app = create_app()
    app.run(host='0.0.0.0', port=8080)
