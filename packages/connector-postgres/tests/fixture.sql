-- Disposable fixture: run as an administrator on a throwaway server only.
DROP SCHEMA IF EXISTS hubtest CASCADE;
CREATE SCHEMA hubtest;
CREATE TABLE hubtest.customers (id int PRIMARY KEY, name text NOT NULL, legacy int);
ALTER TABLE hubtest.customers DROP COLUMN legacy;
COMMENT ON TABLE hubtest.customers IS 'Customer master';
COMMENT ON COLUMN hubtest.customers.name IS 'Display name';
CREATE TABLE hubtest.orders (id int PRIMARY KEY, customer_id int REFERENCES hubtest.customers(id));
CREATE TABLE hubtest.order_lines (
  order_id int, line_no int, amount numeric(12, 2),
  PRIMARY KEY (line_no, order_id),
  CONSTRAINT order_lines_order_fk FOREIGN KEY (order_id) REFERENCES hubtest.orders(id)
);
CREATE TABLE hubtest.events (at date NOT NULL, kind text) PARTITION BY RANGE (at);
CREATE TABLE hubtest.events_2026 PARTITION OF hubtest.events
  FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
CREATE VIEW hubtest.order_totals AS SELECT order_id, sum(amount) AS total FROM hubtest.order_lines GROUP BY order_id;
CREATE TABLE hubtest.payroll (id int PRIMARY KEY);
DROP ROLE IF EXISTS hubtest_reader;
CREATE ROLE hubtest_reader LOGIN PASSWORD 'hubtest-reader';
GRANT USAGE ON SCHEMA hubtest TO hubtest_reader;
GRANT SELECT ON hubtest.customers, hubtest.orders, hubtest.order_lines, hubtest.events,
  hubtest.order_totals TO hubtest_reader;
