# Oracle dialect notes

- A namespace is an owner (schema). Names are exact: an unquoted `hr` is stored as `HR`, and a quoted
  `"Mixed Case"` stays as written. The connector never changes their case.
- The catalog name is the service name you configured, because TAREL passes it back on refresh.
- Without a namespace, every owner this account can see is read, except Oracle-maintained ones
  (`ALL_USERS.ORACLE_MAINTAINED`, available since 12.1).
- `ALL_*` views show only what the account may access. An object without rights looks exactly like
  an object that does not exist.
- Only enabled constraints count. A foreign key to an object this account cannot see is left out.
- Every query binds its values and runs inside `SET TRANSACTION READ ONLY`, which also gives all
  of them one consistent view.
