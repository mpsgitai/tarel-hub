-- Disposable fixture for FREEPDB1: run as SYSTEM on a throwaway server only.
WHENEVER SQLERROR EXIT FAILURE
BEGIN
  FOR u IN (SELECT username FROM all_users WHERE username IN ('HUBTEST', 'HUBTEST_READER')) LOOP
    EXECUTE IMMEDIATE 'DROP USER ' || u.username || ' CASCADE';
  END LOOP;
END;
/
CREATE USER hubtest NO AUTHENTICATION QUOTA UNLIMITED ON users;
CREATE TABLE hubtest.customers (id NUMBER(10) PRIMARY KEY, name VARCHAR2(80) NOT NULL);
COMMENT ON TABLE hubtest.customers IS 'Customer master';
COMMENT ON COLUMN hubtest.customers.name IS 'Display name';
CREATE TABLE hubtest.orders (
  id NUMBER(10) PRIMARY KEY,
  customer_id NUMBER(10) CONSTRAINT orders_customer_fk REFERENCES hubtest.customers(id)
);
CREATE TABLE hubtest.order_lines (
  order_id NUMBER(10), line_no NUMBER(5), amount NUMBER(12, 2),
  CONSTRAINT order_lines_pk PRIMARY KEY (line_no, order_id),
  CONSTRAINT order_lines_order_fk FOREIGN KEY (order_id) REFERENCES hubtest.orders(id)
);
CREATE TABLE hubtest."MixedCase" ("Quoted Column" VARCHAR2(10));
CREATE VIEW hubtest.order_totals AS
  SELECT order_id, SUM(amount) AS total FROM hubtest.order_lines GROUP BY order_id;
CREATE TABLE hubtest.payroll (id NUMBER(10) PRIMARY KEY);
CREATE USER hubtest_reader IDENTIFIED BY "hubtest-reader";
GRANT CREATE SESSION TO hubtest_reader;
GRANT SELECT ON hubtest.customers TO hubtest_reader;
GRANT SELECT ON hubtest.orders TO hubtest_reader;
GRANT SELECT ON hubtest.order_lines TO hubtest_reader;
GRANT SELECT ON hubtest."MixedCase" TO hubtest_reader;
GRANT SELECT ON hubtest.order_totals TO hubtest_reader;
EXIT
