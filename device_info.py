import json
import os

import mysql.connector
import xmltodict
from ncclient import manager
from lxml import etree


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


def get_ospf_config(device_id):
    device = db_derivation(device_id)

    # You can remove the filter entirely OR use native as a broad root filter
    filter_xml = """
        <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native"/>
        """

    with manager.connect(
            host=device["host"],
            port=device["port"],
            username=device["username"],
            password=device["password"],
            hostkey_verify=False
    ) as m:
        response = m.get_config(source='running', filter=("subtree", filter_xml))
        data = xmltodict.parse(response.xml)

        try:
            native_config = data['rpc-reply']['data']['native']
            print(json.dumps(native_config, indent=2))
        except KeyError:
            print("No configuration data found under native.")


def get_all_interface_ips(device_id):
    device = db_derivation(device_id)

    filter_xml = """
    <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    </interfaces>
    """

    with manager.connect(
            host=device["host"],
            port=device["port"],
            username=device["username"],
            password=device["password"],
            hostkey_verify=False
    ) as m:
        response = m.get_config(source="running", filter=("subtree", filter_xml))
        data = xmltodict.parse(response.xml)

        interfaces = data.get('rpc-reply', {}) \
            .get('data', {}) \
            .get('interfaces', {}) \
            .get('interface', [])

        if not isinstance(interfaces, list):
            interfaces = [interfaces]

        interface_ip_map = []

        for interface in interfaces:
            name = interface.get('name', 'unknown')

            ipv4_info = interface.get('ipv4', {}).get('address', {})

            if isinstance(ipv4_info, list):
                for ip_entry in ipv4_info:
                    interface_ip_map.append({
                        "interface": name,
                        "ip_address": ip_entry.get("ip"),
                        "netmask": ip_entry.get("netmask")
                    })
            elif isinstance(ipv4_info, dict):
                interface_ip_map.append({
                    "interface": name,
                    "ip_address": ipv4_info.get("ip"),
                    "netmask": ipv4_info.get("netmask")
                })

        return interface_ip_map
