import json
from dataclasses import asdict
from typing import Optional, Sequence

import click

from snuba import settings
from snuba.consumers.consumer_config import resolve_consumer_config
from snuba.datasets.storages.factory import get_writable_storage_keys


@click.command()
@click.option(
    "--storage",
    "storage_names",
    type=click.Choice(
        [storage_key.value for storage_key in get_writable_storage_keys()]
    ),
    help="The storage to target",
    multiple=True,
    required=True,
)
@click.option(
    "--consumer-group",
    help="Consumer group use for consuming the raw events topic.",
    required=True,
)
@click.option(
    "--auto-offset-reset",
    default="error",
    type=click.Choice(["error", "earliest", "latest"]),
    help="Kafka consumer auto offset reset.",
)
@click.option("--raw-events-topic", help="Topic to consume raw events from.")
@click.option(
    "--commit-log-topic",
    help="Topic for committed offsets to be written to, triggering post-processing task(s)",
)
@click.option(
    "--replacements-topic",
    help="Topic to produce replacement messages info.",
)
@click.option(
    "--bootstrap-server",
    "bootstrap_servers",
    multiple=True,
    help="Kafka bootstrap server to use for consuming.",
)
@click.option(
    "--commit-log-bootstrap-server",
    "commit_log_bootstrap_servers",
    multiple=True,
    help="Kafka bootstrap server to use to produce the commit log.",
)
@click.option(
    "--replacement-bootstrap-server",
    "replacement_bootstrap_servers",
    multiple=True,
    help="Kafka bootstrap server to use to produce replacements.",
)
@click.option(
    "--slice-id",
    "slice_id",
    type=int,
    help="The slice id for the storage",
)
@click.option(
    "--max-batch-size",
    default=settings.DEFAULT_MAX_BATCH_SIZE,
    type=int,
    help="Max number of messages to batch in memory before writing to Kafka.",
)
@click.option(
    "--max-batch-time-ms",
    default=settings.DEFAULT_MAX_BATCH_TIME_MS,
    type=int,
    help="Max length of time to buffer messages in memory before writing to Kafka.",
)
@click.option(
    "--log-level",
    "log_level",
    type=click.Choice(["error", "warn", "info", "debug", "trace"]),
    help="Logging level to use.",
    default="info",
)
@click.option(
    "--no-skip-write",
    "no_skip_write",
    is_flag=True,
    help="Writes to ClickHouse.",
    default=False,
)
def rust_consumer(
    *,
    storage_names: Sequence[str],
    consumer_group: str,
    auto_offset_reset: str,
    raw_events_topic: Optional[str],
    commit_log_topic: Optional[str],
    replacements_topic: Optional[str],
    bootstrap_servers: Sequence[str],
    commit_log_bootstrap_servers: Sequence[str],
    replacement_bootstrap_servers: Sequence[str],
    slice_id: Optional[int],
    max_batch_size: int,
    max_batch_time_ms: int,
    log_level: str,
    no_skip_write: bool,
) -> None:
    """
    Experimental alternative to `snuba consumer`
    """

    consumer_config = resolve_consumer_config(
        storage_names=storage_names,
        raw_topic=raw_events_topic,
        commit_log_topic=commit_log_topic,
        replacements_topic=replacements_topic,
        bootstrap_servers=bootstrap_servers,
        commit_log_bootstrap_servers=commit_log_bootstrap_servers,
        replacement_bootstrap_servers=replacement_bootstrap_servers,
        max_batch_size=max_batch_size,
        max_batch_time_ms=max_batch_time_ms,
        slice_id=slice_id,
    )

    consumer_config_raw = json.dumps(asdict(consumer_config))

    import os

    import rust_snuba

    os.environ["RUST_LOG"] = log_level

    rust_snuba.consumer(  # type: ignore
        consumer_group,
        auto_offset_reset,
        consumer_config_raw,
        not no_skip_write,
    )
