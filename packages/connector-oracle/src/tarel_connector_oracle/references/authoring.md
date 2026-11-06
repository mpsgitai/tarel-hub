# Oracle connector evidence

## Official sources

- python-oracledb installation guide: Thin mode connects to Oracle Database 12.1 or later and does
  not need Oracle Client libraries. Read on 2026-11-04.
- python-oracledb module API: `connect()` parameters `user`, `password`, `host`, `port`,
  `service_name`, `protocol`, `tcp_connect_timeout`. Read on 2026-11-04.

## Status of the evidence

No Oracle Database was available. Queries were reviewed against the documented catalog views and
exercised with a scripted fake driver; they have never run against a real server.
