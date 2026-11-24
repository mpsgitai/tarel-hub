"""Create the disposable hubtest fixture on a throwaway server: ``python fixture.py ADMIN_URL``."""

import sys

from pymongo import MongoClient


def main(admin_url: str) -> None:
    with MongoClient(admin_url, serverSelectionTimeoutMS=5000) as client:
        hub = client["hubtest"]
        # Users and roles outlive dropDatabase; remove them so the fixture can be rerun.
        hub.command("dropAllUsersFromDatabase")
        hub.command("dropAllRolesFromDatabase")
        client.drop_database("hubtest")
        hub.orders.insert_one({"order": 1, "status": "synthetic"})
        hub.command("create", "orderView", viewOn="orders", pipeline=[{"$project": {"status": 1}}])
        hub.command(
            "createRole",
            "listOnly",
            privileges=[
                {"resource": {"db": "hubtest", "collection": ""}, "actions": ["listCollections"]}
            ],
            roles=[],
        )
        hub.command("createUser", "hubtest_lister", pwd="hubtest-lister", roles=["listOnly"])


if __name__ == "__main__":
    main(sys.argv[1])
