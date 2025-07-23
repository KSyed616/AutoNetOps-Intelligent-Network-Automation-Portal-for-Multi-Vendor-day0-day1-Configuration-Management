import os

import mysql.connector
from ncclient import manager


def day1_hello(device_id: int):
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "AutoNetOps")
    )
    db_cursor = conn.cursor()
    db_cursor.execute("SELECT * FROM device WHERE device_id = %s", (device_id,))
    row = db_cursor.fetchone()

    device = {
        "host": row[2],
        "port": row[4],
        "username": row[5],
        "password": row[6]
    }

    with manager.connect(host=device["host"],
                         port=device["port"],
                         username=device["username"],
                         password=device["password"],
                         hostkey_verify=False,
                         device_params={"name": "default"},
                         allow_agent=False,
                         look_for_keys=False) as m:
        print("Supported YANG modules via NETCONF capabilities:\n")
        for capability in m.server_capabilities:
            print(capability)

