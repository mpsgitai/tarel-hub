# TAREL connector-mongodb

Read-only MongoDB metadata connector using `pymongo`. Lists accessible collections and views without reading document payloads unless explicitly configured.

## Install

```sh
uv pip install "git+https://github.com/mpsgitai/tarel-hub.git#subdirectory=packages/connector-mongodb"
tarel connector check mongodb
```

## Configuration & Auth

Use section `[mongodb]` with key `url` or environment variable `TAREL_MONGODB_URL`, e.g. `mongodb://reader:PASSWORD@host:27017/db`. URL credentials only.
