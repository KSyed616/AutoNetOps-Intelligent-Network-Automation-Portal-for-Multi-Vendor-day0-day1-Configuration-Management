import os
from typing import List

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


def gen_int_temp(fields: List[str], ipv4_prefix_option: str):
    template_str = """<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
      <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
        <interface>
          <name>{{ name }}</name>
          <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
    """

    # Append selected fields
    if "description" in fields:
        template_str += "      <description>{{ description }}</description>\n"

    if "enabled" in fields:
        template_str += "      <enabled>{{ enabled }}</enabled>\n"

    if "link-up-down-trap-enable" in fields:
        template_str += "      <link-up-down-trap-enable>{{ link_up_down_trap_enable }}</link-up-down-trap-enable>\n"

    # IPv4 Section
    template_str += """      <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip">
            <address>
              <ip>{{ ipv4_address }}</ip>
    """
    if ipv4_prefix_option == "prefix-length":
        template_str += "          <prefix-length>{{ prefix_length }}</prefix-length>\n"
    else:
        template_str += "          <netmask>{{ netmask }}</netmask>\n"

    template_str += "        </address>\n"

    if "ipv4-enabled" in fields:
        template_str += "        <enabled>{{ ipv4_enabled }}</enabled>\n"
    if "ipv4-forwarding" in fields:
        template_str += "        <forwarding>{{ ipv4_forwarding }}</forwarding>\n"
    if "ipv4-mtu" in fields:
        template_str += "        <mtu>{{ ipv4_mtu }}</mtu>\n"
    if "ipv4-neighbor-ip" in fields:
        template_str += """        <neighbor>
              <ip>{{ ipv4_neighbor_ip }}</ip>\n"""
        if "ipv4-neighbor-mac" in fields:
            template_str += "          <link-layer-address>{{ ipv4_neighbor_mac }}</link-layer-address>\n"
        template_str += "        </neighbor>\n"
    elif "ipv4-neighbor-mac" in fields:
        template_str += """        <neighbor>
              <link-layer-address>{{ ipv4_neighbor_mac }}</link-layer-address>
            </neighbor>\n"""

    template_str += """      </ipv4>
        </interface>
      </interfaces>
    </config>
    """

    # Save template to file
    os.makedirs("templates/generated", exist_ok=True)
    with open("templates/interface_template.j2", "w") as f:
        f.write(template_str)
