"""
RabbitMQ task publishing interface for the Grad School Cafe web application.

This module provides a lightweight client for publishing task messages to a
RabbitMQ broker over AMQP. It declares a durable direct exchange and queue
on every connection, ensuring the required AMQP topology exists before any
message is sent.

Messages are JSON-encoded and published with delivery mode 2 (persistent),
so they survive broker restarts. Each message envelope carries a ``kind``
field identifying the task type, a UTC ISO-8601 timestamp, and an arbitrary
``payload`` dict for task-specific parameters.

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

**Message envelope schema:**

.. code-block:: json

    {
        "kind": "scrape_new_data",
        "ts":   "2026-06-28T14:32:00.123456+00:00",
        "payload": {}
    }

.. note::
    A new AMQP connection is opened and closed for every call to
    :func:`publish_task`. This is intentional for simplicity; for
    high-throughput scenarios a persistent connection pool should be
    considered.

:module: tasks
:synopsis: RabbitMQ task publisher.
"""
import json
import os
from datetime import datetime, timezone
import pika

EXCHANGE = "tasks"
QUEUE = "tasks_q"
ROUTING_KEY = "tasks"

def _open_channel():
    """
    Open a new AMQP connection and declare durable AMQP entities idempotently.

    Reads the broker URL from the ``RABBITMQ_URL`` environment variable,
    establishes a :class:`pika.BlockingConnection`, and declares the
    exchange, queue, and binding required by this application. All entities
    are declared as durable so they survive broker restarts. Declarations
    are idempotent — calling this function multiple times is safe provided
    the entity parameters do not change.

    **Environment variables:**

    +------------------+----------------------------------------------+
    | Variable         | Description                                  |
    +==================+==============================================+
    | ``RABBITMQ_URL`` | AMQP connection URL, e.g.                    |
    |                  | ``amqp://user:pass@rabbitmq:5672/``          |
    +------------------+----------------------------------------------+

    :raises KeyError: If ``RABBITMQ_URL`` is not set in the environment.
    :raises pika.exceptions.AMQPConnectionError: If the broker is
        unreachable or authentication fails.
    :returns: A 2-tuple of ``(connection, channel)`` ready for publishing.
    :rtype: tuple[pika.BlockingConnection, pika.channel.Channel]
    """
    url = os.environ["RABBITMQ_URL"]
    params = pika.URLParameters(url)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    # Durable exchange & queue; bind once per process (idempotent)
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)
    ch.queue_declare(queue=QUEUE, durable=True)
    ch.queue_bind(exchange=EXCHANGE, queue=QUEUE, routing_key=ROUTING_KEY)
    return conn, ch

def publish_task(kind: str, payload: dict | None = None, headers: dict | None = None) -> None:
    """
    Publish a persistent task message to the RabbitMQ task exchange.

    Constructs a JSON message envelope containing the task ``kind``, a
    UTC ISO-8601 timestamp, and the supplied ``payload``, then publishes
    it to the ``tasks`` exchange with delivery mode 2 (persistent). Opens
    a new AMQP connection via :func:`_open_channel` and closes it in a
    ``finally`` block regardless of whether the publish succeeds.

    **Message envelope:**

    +-------------+---------------------------+-------------------------------+
    | Field       | Type                      | Description                   |
    +=============+===========================+===============================+
    | ``kind``    | ``str``                   | Task type identifier          |
    +-------------+---------------------------+-------------------------------+
    | ``ts``      | ``str`` (ISO-8601 UTC)    | Publish timestamp             |
    +-------------+---------------------------+-------------------------------+
    | ``payload`` | ``dict``                  | Task-specific parameters      |
    +-------------+---------------------------+-------------------------------+

    **Supported task kinds:**

    +-------------------------+------------------------------------------+
    | Kind                    | Description                              |
    +=========================+==========================================+
    | ``scrape_new_data``     | Trigger a scrape of new applicant data   |
    +-------------------------+------------------------------------------+
    | ``recompute_analytics`` | Refresh the compiled analytics view      |
    +-------------------------+------------------------------------------+

    :param kind: Task type identifier consumed by the worker. Must match
        a handler registered in the worker's ``received_message`` callback.
    :type kind: str
    :param payload: Optional dict of task-specific parameters passed to
        the worker handler. Defaults to an empty dict if not supplied.
    :type payload: dict | None
    :param headers: Optional AMQP message headers included in
        :class:`pika.BasicProperties`. Defaults to an empty dict if not
        supplied.
    :type headers: dict | None
    :raises pika.exceptions.AMQPConnectionError: If the broker is
        unreachable.
    :raises pika.exceptions.UnroutableError: If the message cannot be
        routed and ``mandatory=True`` is set.
    :returns: None
    :rtype: None

    .. code-block:: python

        # Trigger a data scrape
        publish_task("scrape_new_data")

        # Trigger an analytics recompute with a payload
        publish_task("recompute_analytics", payload={"force": True})
    """
    body_data = {"kind": kind,
                 "ts": datetime.now(timezone.utc).isoformat(),
                 "payload": payload or {}}
    body = json.dumps(body_data).encode("utf-8")
    conn, ch = _open_channel()
    try:
        ch.basic_publish(
            exchange=EXCHANGE,
            routing_key=ROUTING_KEY,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2, headers=headers or {}),
            mandatory=False,
        )
        # If using confirms:
        # if not ch.wait_for_confirms():
        # raise RuntimeError("Publish not confirmed")
    finally:
        conn.close()
