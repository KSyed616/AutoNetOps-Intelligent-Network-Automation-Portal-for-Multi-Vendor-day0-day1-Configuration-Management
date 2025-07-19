import os
import re

import requests
import netmiko
import mysql.connector
from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader

from schema import Login, Device


def cml_login(info: Login):
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "AutoNetOps")
    )

    CML_URL = info.cml_url
    user = info.username
    password = info.pwd

    url = CML_URL + "/api/v0/authenticate"

    response = requests.post(
        url,
        json={
            "username": user,
            "password": password
        },
        verify=False
    )

    if response.status_code == 200:
        token = response.text
        headers = {
            "Authorization": f"Bearer {token}"
        }
        url = CML_URL + "/api/v0/labs"

        response = requests.get(
            url,
            headers=headers,
            verify=False
        )

        lab_id = response.text

        db_cursor = conn.cursor()
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

        return token
    else:
        print(response.text)


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


def day0(cml_url):
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "AutoNetOps")
    )

    db_cursor = conn.cursor()
    db_cursor.execute("SELECT * FROM cmlData WHERE cml_url = %s", cml_url)
    row = db_cursor.fetchone()

    cml_url = row[0]
    token = row[3]
    lab_id = row[4]

    headers = {
        "Authorization": f"Bearer {token}"
    }
    url = cml_url + f"/api/v0/labs/{lab_id}/nodes"

    response = requests.get(
        url,
        headers=headers,
        verify=False
    )

    nodes = response.json()

    for node_id in nodes:
        node_type = identify_node(headers, cml_url, lab_id, node_id)

        db_cursor.execute("SELECT * FROM device WHERE node_id = %s", node_id)
        row = db_cursor.fetchone()

        context = {
            "hostname": row[1],
            "mgmt_int": "GigabitEthernet1",
            "mgmt_ip": row[2],
            "mgmt_mask": "255.255.255.0",
            "domain_name": "example.com",
            "username": row[5],
            "password": row[6],
            "ntp_server": "1.1.1.1",
            "syslog_server": "2.2.2.2"
        }


        if node_type == "router":

            configuration = config("day0_router_config.j2", context)
            url = cml_url + f"/api/v0/labs/{lab_id}/nodes/{node_id}"

            response = requests.patch(
                url,
                json={
                    "configuration": configuration,
                },
                headers=headers,
                verify=False
            )
        else:
            configuration = config("day0_switch_config.j2", context)
            url = cml_url + f"/api/v0/labs/{lab_id}/nodes/{node_id}"

            response = requests.patch(
                url,
                json={
                    "configuration": configuration,
                },
                headers=headers,
                verify=False
            )


def identify_node(headers, cml_url, lab_id, node_id):
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "AutoNetOps")
    )
    db_cursor = conn.cursor()

    # Get node info from CML
    url = f"{cml_url}/api/v0/labs/{lab_id}/nodes/{node_id}"
    response = requests.get(url, headers=headers, verify=False)
    node_info = response.json()

    label = node_info["label"]  # CML node label like "Router-1"
    label_suffix = get_suffix(label.lower())

    # Map hostname with matching suffix
    db_cursor.execute("SELECT device_id, hostname FROM device")
    for device_id, hostname in db_cursor.fetchall():
        if get_suffix(hostname.lower()) == label_suffix:
            db_cursor.execute(
                "UPDATE device SET node_id = %s WHERE device_id = %s",
                (node_id, device_id)
            )
            conn.commit()
            break

    db_cursor.close()
    conn.close()

    if node_info["node_definition"] == "cat9000v-s1":
        return "router"
    else:
        return "switch"



def get_suffix(value):
    match = re.search(r"(\d+)$", value)
    return match.group(1) if match else None

def config(template_name, context: dict):
    env = Environment(loader=FileSystemLoader("configurations"))
    temp = env.get_template(template_name)
    return temp.render(context)