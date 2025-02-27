from snuba.admin.audit_log.query import audit_log
from snuba.admin.clickhouse.common import (
    get_ro_query_node_connection,
    validate_ro_query,
)
from snuba.clickhouse.native import ClickhouseResult
from snuba.clusters.cluster import ClickhouseClientSettings
from snuba.datasets.schemas.tables import TableSchema
from snuba.datasets.storages.factory import get_storage
from snuba.datasets.storages.storage_key import StorageKey

# HACK (VOLO): Everything in this file is a hack


def _stringify_result(result: ClickhouseResult) -> ClickhouseResult:
    # javascript stores numbers as doubles so in order for it to not round
    # metric ids (which are all prefixed by (1 << 63)) we strigify them before sending
    # them to the client
    result_rows = []
    for row in result.results:
        result_rows.append([str(col) for col in row])
    return ClickhouseResult(result_rows, result.meta)


@audit_log
def run_metrics_query(query: str, user: str) -> ClickhouseResult:
    """
    Validates, audit logs, and executes given query against Querylog
    table in ClickHouse. `user` param is necessary for audit_log
    decorator.
    """
    schema = get_storage(StorageKey("generic_metrics_distributions")).get_schema()
    assert isinstance(schema, TableSchema)
    validate_ro_query(
        sql_query=query,
        allowed_tables={
            schema.get_table_name(),
            "generic_metric_distributions_aggregated_dist",
        },
    )
    return _stringify_result(__run_query(query))


def __run_query(query: str) -> ClickhouseResult:
    """
    Runs given Query against metrics distributions in ClickHouse. This function assumes valid
    query and does not validate/sanitize query or response data.
    """
    connection = get_ro_query_node_connection(
        StorageKey("generic_metrics_distributions").value,
        ClickhouseClientSettings.TRACING,
    )

    query_result = connection.execute(
        query=query,
        with_column_types=True,
    )
    return query_result
