import requests
import netmiko
import mysql.connector
from mysql.connector import cursor

from schema import Login, Device

def cml_login(info: Login):
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
        print("Authenticated with token: " + token)
    else:
        print(response.text)


def day0(device: Device):
    conn = mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="password",
        database="AutoNetOps"
    )

    db_cursor = conn.cursor()
    sql = """
    INSERT INTO device (hostname, ip_address, platform, username, password)
    VALUES (%s, %s, %s, %s, %s)
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

    
