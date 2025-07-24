import os

import mysql.connector
import xmltodict
from ncclient import manager


def db_derivation(device_id: int):
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

    return device


def day1_hello(device_id: int):
    device = db_derivation(device_id)

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


def get_interfaces(device_id: int):
    device = db_derivation(device_id)

    filter_xml = """
    <interfaces-state xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
    """

    with manager.connect(
            host=device["host"],
            port=device["port"],
            username=device["username"],
            password=device["password"],
            hostkey_verify=False
    ) as m:
        response = m.get(filter=("subtree", filter_xml))
        data = xmltodict.parse(response.xml)

        interfaces = data['rpc-reply']['data']['interfaces-state']['interface']

        unconfigured = []
        for intf in interfaces:
            name = intf.get("name")
            oper_status = intf.get("oper-status", "down")
            intf.get("phys-address", None)
            intf.get("speed", None)

            if oper_status == "down":
                unconfigured.append({
                    "name": name,
                    "status": "Disabled"
                })

    return unconfigured

