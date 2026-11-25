# TAREL lineage-sqlglot

Konservative, schreibzentrierte statische SQL-Lineage-Analyse für TAREL über das Entry-Point-Interface `tarel.lineage_analyzers`.

Aus dem Hub im eigenen TAREL-Environment installieren:

```sh
uv pip install --index-url https://pypi.org/simple ./packages/lineage-sqlglot
tarel lineage analyze <lineage> --source <file> --analyzer sqlglot
```

Unterstützte Dialekte: DuckDB, PostgreSQL, SQLite, SQL Server (`tsql`).
`sqlglot` wird als reguläre PyPI-Dependency bezogen und nicht im Paket gebündelt.
