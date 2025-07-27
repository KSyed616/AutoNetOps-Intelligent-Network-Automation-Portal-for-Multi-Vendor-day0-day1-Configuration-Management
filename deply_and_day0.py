import os
import re
import time

import mysql.connector
import requests
from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader

from schema import Login, Device
from vendor import ciscoHandler, juniperHandler
from vendor.ciscoHandler import CiscoHandler
from vendor.juniperHandler import JuniperHandler


def cml_login():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "AutoNetOps")
    )

    CML_URL = "https://10.10.133.57"
    user = "admin"
    password = "CompNet1234"

    url = CML_URL + "/api/v0/authenticate"

    response = requests.post(
        url,
        json={
            "username": user,
            "password": password
        },
        verify=False
    )
    print("resp ", response.status_code)
    print("CML: ", CML_URL)

    if response.status_code == 200:
        token = response.text.strip('"')
        headers = {
            "Authorization": f"Bearer {token}"
        }
        url = CML_URL + "/api/v0/labs"

        response = requests.get(
            url,
            headers=headers,
            verify=False
        )
        labs = response.json()
        lab_id = labs[0]

        db_cursor = conn.cursor()
        sql = """
                SELECT * FROM cmlData WHERE cml_url = %s
            """

        db_cursor.execute(sql, (CML_URL,))
        row = db_cursor.fetchone()
        print("this is row:", row)

        if not row:
            sql = """
                    INSERT INTO cmlData (cml_url, username, password, token, lab_id)
                    VALUES (%s, %s, %s, %s, %s)
                   """
            values = (CML_URL,
                      user,
                      password,
                      token,
                      lab_id)

            db_cursor.execute(sql, values)
            conn.commit()

            db_cursor.close()
            conn.close()
        else:
            sql = """
                      UPDATE cmlData SET token = %s WHERE cml_url = %s
                   """
            values = (token, CML_URL)
            db_cursor.execute(sql, values)
            conn.commit()

            db_cursor.close()
            conn.close()

        return token
    else:
        print(response.text)
        return None


def get_deployed():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "AutoNetOps")
    )

    db_cursor = conn.cursor()
    db_cursor.execute("SELECT * FROM device")
    rows = db_cursor.fetchall()
    db_cursor.close()
    conn.close()
    return rows


def get_day0():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "AutoNetOps")
    )

    db_cursor = conn.cursor(dictionary=True)
    db_cursor.execute("SELECT * FROM device")
    rows = db_cursor.fetchall()
    db_cursor.close()
    conn.close()
    return rows


def deploy(device: Device):
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "AutoNetOps")
    )

    db_cursor = conn.cursor()
    sql = """
    INSERT INTO device (hostname, ip_address, platform, netconf_port, username, password, device_type)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    values = (device.hostname,
              device.ip_address,
              device.platform,
              830,
              device.username,
              device.password,
              device.device_type)

    db_cursor.execute(sql, values)
    conn.commit()

    db_cursor.close()
    conn.close()


def edit_onboard(device_id: int, device: Device):
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "AutoNetOps")
    )

    db_cursor = conn.cursor()
    db_cursor.execute("SELECT * FROM device WHERE device_id = %s", (device_id,))

    if db_cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Device not found")

    sql = """
        UPDATE device SET hostname = %s,
            ip_address = %s,
            platform = %s,
            netconf_port = %s,
            username = %s,
            password = %s,
            device_type = %s
        WHERE device_id = %s
        """

    values = (device.hostname,
              device.ip_address,
              device.platform,
              830,
              device.username,
              device.password,
              device.device_type,
              device_id)

    db_cursor.execute(sql, values)
    conn.commit()

    db_cursor.close()
    conn.close()


def day0():
    cml_url = "https://10.10.133.57"

    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "AutoNetOps")
    )
    db_cursor = conn.cursor()
    db_cursor.execute("SELECT * FROM cmlData WHERE cml_url = %s", (cml_url,))
    row = db_cursor.fetchone()

    token = row[3]
    lab_id = row[4]

    headers = {"Authorization": f"Bearer {token}"}

    requests.put(f"{cml_url}/api/v0/labs/{lab_id}/stop", headers=headers, verify=False)
    time.sleep(3)
    requests.put(f"{cml_url}/api/v0/labs/{lab_id}/wipe", headers=headers, verify=False)

    response = requests.get(f"{cml_url}/api/v0/labs/{lab_id}/nodes", headers=headers, verify=False)
    nodes = response.json()

    for node_id in nodes:
        identify_node(headers, cml_url, lab_id, node_id)

    db_cursor.execute("SELECT * FROM device")
    devices = db_cursor.fetchall()

    for row in devices:
        node_id = row[8]
        if not node_id:
            continue

        device_type = row[7].lower()
        mgmt_int = "Vlan1" if device_type == "switch" else "GigabitEthernet1"
        default_gw = get_default_gateway(row[2]) if device_type == "switch" else None

        context = {
            "hostname": row[1],
            "mgmt_int": mgmt_int,
            "mgmt_ip": row[2],
            "mgmt_mask": "255.255.255.0",
            "domain_name": "example.com",
            "username": row[5],
            "password": row[6],
            "ntp_server": "1.1.1.1",
            "syslog_server": "2.2.2.2",
            "default_gw": default_gw
        }

        platform = row[3].lower()
        device_type = row[7].lower()
        template = f"{platform}/day0_{device_type}_config.j2"

        configuration = config(template, context)
        print("config ", configuration)

        handler = get_vendor_handler(platform)
        handler.push_config(cml_url, lab_id, node_id, headers, configuration)

    db_cursor.close()
    conn.close()


def day0_single(device_id: int):
    cml_url = "https://10.10.133.57"

    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "AutoNetOps")
    )
    db_cursor = conn.cursor()

    db_cursor.execute("SELECT * FROM cmlData WHERE cml_url = %s", (cml_url,))
    row = db_cursor.fetchone()
    token = row[3]
    lab_id = row[4]
    headers = {"Authorization": f"Bearer {token}"}

    db_cursor.execute("SELECT * FROM device WHERE device_id = %s", (device_id,))
    row = db_cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Device not found")

    node_id = row[8]

    requests.put(
        f"{cml_url}/api/v0/labs/{lab_id}/nodes/{node_id}/state/stop",
        headers=headers,
        verify=False
    )
    time.sleep(2)

    requests.put(
        f"{cml_url}/api/v0/labs/{lab_id}/nodes/{node_id}/wipe_disks",
        headers=headers,
        verify=False
    )

    if not node_id:
        raise HTTPException(status_code=400, detail="Node ID not set for this device.")

    device_type = row[7].lower()
    mgmt_int = "Vlan1" if device_type == "switch" else "GigabitEthernet1"
    default_gw = get_default_gateway(row[2]) if device_type == "switch" else None

    context = {
        "hostname": row[1],
        "mgmt_int": mgmt_int,
        "mgmt_ip": row[2],
        "mgmt_mask": "255.255.255.0",
        "domain_name": "example.com",
        "username": row[5],
        "password": row[6],
        "ntp_server": "1.1.1.1",
        "syslog_server": "2.2.2.2",
        "default_gw": default_gw
    }

    platform = row[3].lower()
    template = f"{platform}/day0_{device_type}_config.j2"

    configuration = config(template, context)

    handler = get_vendor_handler(platform)
    handler.push_config(cml_url, lab_id, node_id, headers, configuration)

    db_cursor.close()
    conn.close()


def identify_node(headers, cml_url, lab_id, node_id):
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "AutoNetOps")
    )
    db_cursor = conn.cursor()

    url = f"{cml_url}/api/v0/labs/{lab_id}/nodes/{node_id}"
    response = requests.get(url, headers=headers, verify=False)
    node_info = response.json()

    label = node_info["label"].strip().lower()

    db_cursor.execute("SELECT device_id, hostname FROM device")
    for device_id, hostname in db_cursor.fetchall():
        if hostname.strip().lower() == label.strip().lower():
            db_cursor.execute(
                "UPDATE device SET node_id = %s WHERE device_id = %s",
                (node_id, device_id)
            )
            conn.commit()

    db_cursor.close()
    conn.close()


def get_vendor_handler(platform):
    vendor_map = {
        "cisco": CiscoHandler,
        "juniper": JuniperHandler
    }
    handler_class = vendor_map.get(platform.lower())
    if handler_class:
        return handler_class()
    else:
        raise ValueError(f"Unsupported vendor platform: {platform}")


def get_default_gateway(ip_address: str):
    parts = ip_address.strip().split(".")
    if len(parts) == 4:
        parts[-1] = "1"
        return ".".join(parts)
    else:
        raise ValueError("Invalid IP address format")


def config(template_name, context: dict):
    env = Environment(loader=FileSystemLoader("configurations"))
    temp = env.get_template(template_name)
    return temp.render(context)
