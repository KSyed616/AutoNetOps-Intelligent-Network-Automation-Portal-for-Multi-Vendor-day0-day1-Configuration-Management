import os

import requests
import netmiko
import mysql.connector
from fastapi import HTTPException

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
    INSERT INTO device (hostname, ip_address, platform, netconf_port, username, password)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    values = (device.hostname,
              device.ip_address,
              device.platform,
              830,
              device.username,
              device.password)

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
            password = %s
        WHERE device_id = %s
        """

    values = (device.hostname,
              device.ip_address,
              device.platform,
              830,
              device.username,
              device.password,
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
        if node_type == "router":

            url = cml_url + f"/api/v0/labs/{lab_id}/nodes/{node_id}"

            response = requests.patch(
                url,
                json={

                },
                headers=headers,
                verify=False
            )


            "router config"
        else:
            "switch config"

def identify_node(headers, cml_url, lab_id, node_id):

    url = cml_url + f"/api/v0/labs/{lab_id}/nodes/{node_id}"

    response = requests.get(
        url,
        headers=headers,
        verify=False
    )

    node_info = response.json()

    if node_info["node_definition"] == "cat9000v-s1":
        return "router"
    else:
        return "switch"







