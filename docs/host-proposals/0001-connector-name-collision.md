# Proposal 0001: Connector Name Collisions

**Status: implemented in TAREL host.**

`tarel.connectors.host.load_manifest` now raises `ambiguous_connector` whenever an installed third-party entry point collides with a built-in connector name, instead of silently shadowing the external package. `contract-tests/test_host_loading.py` verifies this behavior against the host.
