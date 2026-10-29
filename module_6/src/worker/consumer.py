"""
RabbitMQ message consumer and database update worker for the Grad School
Cafe data pipeline.

This module implements a long-running AMQP consumer that listens for task
messages published by the web application and dispatches them to the
appropriate handler. Two task types are supported: scraping new applicant
data from the Grad Cafe website and recomputing the compiled analytics
materialized view.

Each message is processed within a single psycopg3 database transaction.
On success the message is acknowledged; on failure it is negatively
acknowledged without requeue, and the error is logged to stdout.

**Supported task kinds:**

+-------------------------+--------------------------------------------------+
| Kind                    | Handler                                          |
+=========================+==================================================+
| ``scrape_new_data``     | :func:`handle_scrape_new_data`                   |
+-------------------------+--------------------------------------------------+
| ``recompute_analytics`` | :func:`handle_recompute_analytics`               |
+-------------------------+--------------------------------------------------+

**AMQP topology:**

+----------------+----------+------------------+
| Resource       | Type     | Name             |
+================+==========+==================+
| Exchange       | direct   | ``tasks``        |
+----------------+----------+------------------+
| Queue          | durable  | ``tasks_q``      |
+----------------+----------+------------------+
| Routing key    | —        | ``tasks``        |
+----------------+----------+------------------+

**Environment variables:**

+------------------+---------------------------------------------+
| Variable         | Description                                 |
+==================+=============================================+
| ``RABBITMQ_URL`` | AMQP broker URL                             |
|                  | e.g. ``amqp://user:pass@rabbitmq:5672/``    |
+------------------+---------------------------------------------+
| ``DATABASE_URL`` | psycopg3 connection string                  |
|                  | e.g. ``postgresql://user:pass@db:5432/mydb``|
+------------------+---------------------------------------------+

:module: consumer
:synopsis: RabbitMQ consumer and task dispatcher for the data pipeline worker.
"""

import json
import os
import uuid
from datetime import datetime

import pika
import psycopg
from psycopg.rows import dict_row
from psycopg import errors
from etl.scrape import scrape_data

EXCHANGE = "tasks"
QUEUE = "tasks_q"
ROUTING_KEY = "tasks"

TASK_STATUS_SQL = "UPDATE tasks SET status = %s, error = %s, updated_at = NOW() WHERE task_id = %s;"

def _create_tuples_list(scraped_data):
    """
    Convert a list of application record dictionaries into a list of
    tuples suitable for bulk database insertion.

    Iterates over ``scraped_data``, coercing numeric fields from their
    string representations to ``float``, substituting ``-1.0`` for any
    missing values (stored as the string ``"None"``), and parsing
    ``date_added`` from a human-readable string into a
    :class:`datetime.date` object via the format ``"%b %d, %Y"``. Each
    record is then packed into a 16-element tuple whose column order
    matches the ``applicants`` table schema.

    :param scraped_data: A list of application record dictionaries as
        produced by :func:`etl.scrape.scrape_data`. Records are mutated
        in place during type coercion.
    :type scraped_data: list[dict]
    :returns: A list of 16-element tuples ready for bulk insertion via
        :meth:`psycopg.Cursor.executemany`.
    :rtype: list[tuple]
    """
    insert_data = []
    # Create a list of tuples from the dictionaries to bulk insert
    for datum in scraped_data:
        # Convert datatypes first, missing value assigned as -1 for easier filtering
        if datum["gpa"] == "None":
            datum["gpa"] = -1.0
        else:
            datum["gpa"] = float(datum["gpa"])

        if datum["gre"] == "None":
            datum["gre"] = -1.0
        else:
            datum["gre"] = float(datum["gre"])

        if datum["grev"] == "None":
            datum["grev"] = -1.0
        else:
            datum["grev"] = float(datum["grev"])

        if datum["greaw"] == "None":
            datum["greaw"] = -1.0
        else:
            datum["greaw"] = float(datum["greaw"])

        # Create the tuple for iteration
        insert_data.append((datum["id"],
                        datum["program"],
                        datum["degree"],
                        datum["university"],
                        datum["comments"],
                        datetime.strptime(datum["date_added"],"%b %d, %Y").date(),
                        datum["url"],
                        datum["status"],
                        datum["term"],
                        datum["US/International"],
                        datum["gpa"],
                        datum["gre"],
                        datum["grev"],
                        datum["greaw"],
                        datum["llm-generated-program"],
                        datum["llm-generated-university"]
                        ))
    return insert_data

INSERT_SQL = """
    INSERT INTO applicants (p_id, program, degree, university, comments, date_added, url, status,
    term, us_or_international, gpa, gre, gre_v, gre_aw, llm_generated_program, llm_generated_university)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (p_id) DO NOTHING;
"""

def insert_entries(conn, scraped_data):
    """
    Bulk insert scraped application records into the ``applicants`` table.

    Converts ``scraped_data`` into insertion tuples via
    :func:`_create_tuples_list` and executes a parameterised bulk insert
    using :meth:`psycopg.Cursor.executemany`. Existing records are
    silently skipped via ``ON CONFLICT (p_id) DO NOTHING``. Any exception
    raised during insertion is re-raised to the caller for handling within
    the per-message transaction.

    :param conn: An active psycopg3 database connection. The caller is
        responsible for committing or rolling back the transaction.
    :type conn: psycopg.Connection
    :param scraped_data: A list of application record dictionaries as
        returned by :func:`etl.scrape.scrape_data`.
    :type scraped_data: list[dict]
    :raises Exception: Re-raises any exception thrown by
        :meth:`psycopg.Cursor.executemany`.
    :returns: None
    :rtype: None
    """
    try:
        with conn.cursor() as cur:
            cur.executemany(INSERT_SQL, _create_tuples_list(scraped_data))
    except Exception as e:
        raise e

def _open_channel():
    """
    Open a new AMQP connection and declare durable AMQP entities idempotently.

    Reads the broker URL from the ``RABBITMQ_URL`` environment variable,
    establishes a :class:`pika.BlockingConnection`, and declares the
    direct exchange, durable queue, and binding required by this worker.
    All declarations are idempotent — safe to call on every process start.

    :raises KeyError: If ``RABBITMQ_URL`` is not set in the environment.
    :raises pika.exceptions.AMQPConnectionError: If the broker is
        unreachable or authentication fails.
    :returns: A 2-tuple of ``(connection, channel)`` ready for consuming.
    :rtype: tuple[pika.BlockingConnection, pika.channel.Channel]
    """
    url = os.getenv("RABBITMQ_URL")
    params = pika.URLParameters(url)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    # Durable exchange & queue; bind once per process (idempotent)
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)
    ch.queue_declare(queue=QUEUE, durable=True)
    ch.queue_bind(exchange=EXCHANGE, queue=QUEUE, routing_key=ROUTING_KEY)
    return conn, ch

def handle_scrape_new_data(conn, _payload):
    """
    Scrape new applicant records and persist them to the database.

    Reads the current high-water mark from ``ingestion_watermarks`` for
    source ``'WEB'``, passes it to :func:`etl.scrape.scrape_data` to
    fetch only records newer than the last ingestion, and bulk-inserts any
    returned records via :func:`insert_entries`. If new records were
    inserted, the watermark is updated to the new maximum ``p_id``.

    All database operations share the caller-supplied connection and are
    executed within the same transaction as the enclosing message handler.

    :param conn: An active psycopg3 database connection configured with
        :class:`psycopg.rows.dict_row` as the row factory.
    :type conn: psycopg.Connection
    :param payload: Decoded message payload. Currently unused but accepted
        for interface consistency with other handlers.
    :type payload: dict
    :raises Exception: Re-raises any exception thrown during scraping or
        database operations after logging the error to stdout.
    :returns: ``0`` on success, or ``None`` if no new data was found.
    :rtype: int
    """
    print("Task dispatched to scraper")
    with conn.cursor() as cur:
        cur.execute("SELECT last_seen as last_seen FROM ingestion_watermarks WHERE source='WEB';")
        last_seen_id = cur.fetchone()["last_seen"]
        try:
            new_data = scrape_data(last_seen_id)
            # If no data was scraped, back out gracefully
            if new_data is None:
                print("Scrape complete, no new entries found")
                return

            print("Scrape complete, updating database")
            insert_entries(conn, new_data)
            cur.execute("SELECT MAX(p_id) AS new_max FROM applicants;")
            new_max = cur.fetchone()["new_max"]

            # Update watermark if we have a new max entry
            if new_max > last_seen_id:
                print(f"Updating watermark: {new_max}")
                update_last_seen_sql = "UPDATE ingestion_watermarks SET last_seen = %s, updated_at \
                    = NOW() WHERE source = 'WEB';"
                cur.execute(update_last_seen_sql, (new_max,))
        except Exception as e:
            print(f"Exception caught: {type(e).__name__}: {e}")
            raise e # bare raise preserves full traceback
    print("Update operation complete")

    return

def handle_recompute_analytics(conn, _payload):
    """
    Refresh the ``compiled_analytics`` materialized view.

    Calls the ``refresh_compiled_analytics()`` database function, which
    executes ``REFRESH MATERIALIZED VIEW CONCURRENTLY compiled_analytics``
    within the same per-message transaction as the enclosing message
    handler.

    :param conn: An active psycopg3 database connection configured with
        :class:`psycopg.rows.dict_row` as the row factory.
    :type conn: psycopg.Connection
    :param payload: Decoded message payload. Currently unused but accepted
        for interface consistency with other handlers.
    :type payload: dict
    :returns: None
    :rtype: None
    """
    print("Task dispatched to recompute")
    with conn.cursor() as cur:
        mv_refresh_sql = "SELECT refresh_compiled_analytics();"
        cur.execute(mv_refresh_sql)
        print("Materialized View Updated")

def _set_task_status(task_id, status, error=None):
    """
    Record a task's status in the ``tasks`` table on its own connection.

    Uses a separate short-lived connection so the update commits
    immediately and survives a rollback of the task's own transaction.
    Failures are logged rather than raised, so a status write can never
    stop the consumer. Messages without a ``task_id`` are skipped.

    :param task_id: The task's UUID, or ``None`` if the message had none.
    :type task_id: str | None
    :param status: One of ``running``, ``succeeded`` or ``failed``.
    :type status: str
    :param error: Error text to store with a ``failed`` status.
    :type error: str | None
    :returns: None
    :rtype: None
    """
    if task_id is None:
        return
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            conn.execute(TASK_STATUS_SQL, (status, error, task_id))
    except psycopg.Error as e:
        print(f"Could not mark task {task_id} as {status}: {e}")

def _reject(ch, method, task_id, error):
    """
    Mark a task failed, log the error, and nack its message without requeue.

    :param ch: The pika channel the message was delivered on.
    :type ch: pika.channel.Channel
    :param method: Delivery metadata holding the ``delivery_tag``.
    :type method: pika.spec.Basic.Deliver
    :param task_id: The task's UUID, or ``None`` if the message had none.
    :type task_id: str | None
    :param error: Description of the failure, logged and stored on the task.
    :type error: str
    :returns: None
    :rtype: None
    """
    print(error)
    _set_task_status(task_id, "failed", error)
    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

TASK_HANDLERS = {
    "scrape_new_data": handle_scrape_new_data,
    "recompute_analytics": handle_recompute_analytics,
}

def received_message(ch, method, _properties, body):
    """
    AMQP message callback — decode, dispatch, and acknowledge each task.

    Invoked by pika for every message delivered from ``tasks_q``. Decodes
    the JSON body, looks up the handler for its ``kind`` in
    ``TASK_HANDLERS``, opens a psycopg3 database connection, and runs the
    handler inside a single transaction. Sends a ``basic_ack`` only after
    the transaction commits.

    If the message carries a ``task_id``, the matching ``tasks`` row is
    set to ``running`` before the handler starts, to ``succeeded`` in the
    handler's own transaction, and to ``failed`` (with the error text) on
    any failure.

    Malformed messages (invalid JSON, missing or unknown ``kind``) and any
    handler failure — database errors, scrape HTTP errors, or anything
    else — are rolled back, logged to stdout, and ``basic_nack``-ed
    without requeue. No exception escapes this callback, so a failed task
    never stops the consumer or blocks later messages in the queue.

    :param ch: The pika channel on which the message was delivered. Used
        to send ``basic_ack`` or ``basic_nack``.
    :type ch: pika.channel.Channel
    :param method: Delivery metadata from the broker, including the
        ``delivery_tag`` required for acknowledgement.
    :type method: pika.spec.Basic.Deliver
    :param properties: AMQP message properties (headers, content type,
        etc.). Not used directly by this handler.
    :type properties: pika.spec.BasicProperties
    :param body: Raw message body as UTF-8 encoded JSON bytes.
    :type body: bytes
    :returns: None
    :rtype: None
    """
    print("Message received from RabbitMQ")
    # Reject malformed or unknown messages up front; requeueing would never fix them
    task_id = None
    try:
        message = json.loads(body)
        task_id = message.get("task_id")
        if task_id is not None:
            task_id = str(uuid.UUID(task_id))
        kind = message["kind"]
        handler = TASK_HANDLERS[kind]
        payload = message.get("payload") or {}
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        _reject(ch, method, task_id,
                f"Malformed or unknown task discarded: {type(e).__name__}: {e}")
        return

    _set_task_status(task_id, "running")
    # Leaving the connection block commits on success and rolls back on any
    # exception, so the message is only acked after a successful commit. The
    # succeeded status is written in the same transaction as the task's work.
    try:
        with psycopg.connect(os.getenv("DATABASE_URL"), row_factory=dict_row) as conn:
            handler(conn, payload)
            if task_id is not None:
                conn.execute(TASK_STATUS_SQL, ("succeeded", None, task_id))
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"Task {kind} committed and acknowledged")
    except errors.UniqueViolation as e:
        _reject(ch, method, task_id,
                f"Duplicate record found during bulk insert: {e.diag.message_detail}")
    except errors.NotNullViolation as e:
        _reject(ch, method, task_id, f"Null value in non-nullable column: {e.diag.column_name}")
    except errors.CheckViolation as e:
        _reject(ch, method, task_id, f"Check constraint violated: {e.diag.constraint_name}")
    except errors.UndefinedTable:
        _reject(ch, method, task_id, "Table does not exist")
    except psycopg.OperationalError as e:
        _reject(ch, method, task_id, f"Database connection error: {e}")
    except psycopg.Error as e:
        _reject(ch, method, task_id, f"Unexpected database error: {e}")
    # Any other failure (e.g. scrape HTTP errors) must not kill the consumer
    except Exception as e:  # pylint: disable=broad-exception-caught
        _reject(ch, method, task_id, f"Task {kind} failed: {type(e).__name__}: {e}")

if __name__=='__main__':
    print("Connecting to RabbitMQ")
    rabbit_conn, rabbit_ch = _open_channel()
    rabbit_ch.basic_qos(prefetch_count=1)
    rabbit_ch.basic_consume(queue=QUEUE, on_message_callback=received_message, auto_ack=False)
    print("Starting consume")
    rabbit_ch.start_consuming()
