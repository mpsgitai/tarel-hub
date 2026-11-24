-- Disposable fixture for ClickHouse 25.8: run as an administrator on a throwaway server only.
DROP DATABASE IF EXISTS hubtest;
DROP USER IF EXISTS hubtest_reader;
CREATE DATABASE hubtest;
CREATE TABLE hubtest.orders (
  id UInt32 COMMENT 'Order number', customer_id Nullable(UInt32), amount Decimal(12, 2),
  channel LowCardinality(Nullable(String))
) ENGINE = MergeTree ORDER BY id COMMENT 'Synthetic orders';
CREATE VIEW hubtest.order_totals AS SELECT customer_id, sum(amount) AS total FROM hubtest.orders GROUP BY customer_id;
CREATE TABLE hubtest.payroll (id UInt32) ENGINE = MergeTree ORDER BY id;
CREATE USER hubtest_reader IDENTIFIED WITH sha256_password BY 'hubtest-reader';
GRANT SELECT ON hubtest.orders TO hubtest_reader;
GRANT SELECT ON hubtest.order_totals TO hubtest_reader;
