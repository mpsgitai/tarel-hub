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
