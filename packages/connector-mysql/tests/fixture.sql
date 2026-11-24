-- Disposable fixture for MySQL 8.4 and MariaDB 11.4: run as root on a throwaway server only.
DROP DATABASE IF EXISTS hubtest;
DROP USER IF EXISTS 'hubtest_reader'@'%';
CREATE DATABASE hubtest;
CREATE TABLE hubtest.customers (
  id INT PRIMARY KEY, name VARCHAR(80) NOT NULL COMMENT 'Display name'
) COMMENT 'Customer master';
CREATE TABLE hubtest.orders (
  id INT PRIMARY KEY, customer_id INT,
  CONSTRAINT orders_customer_fk FOREIGN KEY (customer_id) REFERENCES hubtest.customers(id)
);
CREATE TABLE hubtest.order_lines (
  order_id INT, line_no INT, amount DECIMAL(12, 2),
  PRIMARY KEY (line_no, order_id),
  CONSTRAINT order_lines_order_fk FOREIGN KEY (order_id) REFERENCES hubtest.orders(id)
);
CREATE VIEW hubtest.order_totals AS
  SELECT order_id, SUM(amount) AS total FROM hubtest.order_lines GROUP BY order_id;
CREATE TABLE hubtest.payroll (id INT PRIMARY KEY);
CREATE USER 'hubtest_reader'@'%' IDENTIFIED BY 'hubtest-reader';
GRANT SELECT ON hubtest.customers TO 'hubtest_reader'@'%';
GRANT SELECT ON hubtest.orders TO 'hubtest_reader'@'%';
GRANT SELECT ON hubtest.order_lines TO 'hubtest_reader'@'%';
GRANT SELECT ON hubtest.order_totals TO 'hubtest_reader'@'%';
