"""Tests for the TAREL Hub SQLGlot static lineage analyzer plugin."""

from __future__ import annotations

from tarel.lineage.source import SourceDefinition

from tarel_lineage_sqlglot.analyzer import analyze_with_sqlglot, create_analyzer


def _definition(language: str, sql: str) -> SourceDefinition:
    return SourceDefinition(
        external_id="def:test",
        kind="procedure",
        name="usp_refresh",
        qualified_name="dbo.usp_refresh",
        language=language,
        content=sql,
        source_reference="sql/usp_refresh.sql",
    )


def test_create_analyzer_exposes_name_and_analyzes_temp_table_write() -> None:
    analyzer = create_analyzer()
    assert analyzer.name == "sqlglot"
    definition = _definition(
        "tsql",
        "SELECT o.id\n"
        "INTO #Stage\n"
        "FROM raw.Orders o;\n"
        "INSERT INTO mart.Fact\n"
        "SELECT s.id FROM #Stage s JOIN dim.Customer c ON c.id = s.id;",
    )
    result = analyzer.analyze(definition)
    assert result.complete is True
    assert result.dialect == "tsql"
    assert result.analysis is not None
    writes = result.analysis["writes"]
    assert isinstance(writes, list) and len(writes) == 1
    assert writes[0]["target"] == "mart.Fact"
    sources = {item["target"] for item in writes[0]["sources"]}
    assert sources == {"raw.Orders", "dim.Customer"}


def test_unsupported_dialect_returns_sanitized_status() -> None:
    result = analyze_with_sqlglot(_definition("cobol", "SELECT 1"))
    assert result.complete is False
    assert result.failure_code == "sqlglot_unsupported_dialect"


def test_same_line_writes_preserve_statement_order() -> None:
    import sqlglot
    from sqlglot import exp
    from tarel.lineage.coverage import WriteMarker

    from tarel_lineage_sqlglot.analyzer import _match_writes

    sql = "SELECT id INTO #Stage FROM raw.Orders; INSERT INTO mart.Fact SELECT id FROM #Stage;"
    expressions = tuple(item for item in sqlglot.parse(sql, dialect="tsql") if item is not None)
    markers = (
        WriteMarker(operation="select_into", line=1, text=sql),
        WriteMarker(operation="insert", line=1, text=sql),
    )
    matched = _match_writes(expressions, markers, exp)
    assert matched is not None
    assert [w.operation for w in matched] == ["select_into", "insert"]


def test_nested_cte_does_not_shadow_outer_physical_table() -> None:
    sql = (
        "INSERT INTO dst SELECT * FROM orders "
        "UNION ALL SELECT * FROM (WITH orders AS (SELECT * FROM archived_orders) "
        "SELECT * FROM orders) nested;"
    )
    result = analyze_with_sqlglot(_definition("postgres", sql))
    assert result.complete is True
    assert result.analysis is not None
    sources = {item["target"] for item in result.analysis["writes"][0]["sources"]}
    assert sources == {"orders", "archived_orders"}


def test_writable_cte_target_returns_unsupported() -> None:
    sql = "WITH c AS (SELECT * FROM dbo.RealTarget) UPDATE c SET value = 1;"
    result = analyze_with_sqlglot(_definition("tsql", sql))
    assert result.complete is False
