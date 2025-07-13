import requests
import netmiko
import mysql.connector
from mysql.connector import cursor

from schema import Login, Device

#logs into Cisco Modeling Lab (CML) with username and password
#function cml_login. Accepts 'info' of type Login
def cml_login(info: Login):
    #Login info parameters defined in schema
    CML_URL = info.cml_url
    user = info.username
    password = info.pwd

    #constructs full API endpoint for login: expects a POST request
    url = CML_URL + "/api/v0/authenticate"

    #request library to send POST request
    #send credentials as JSON payload
    #no verification yet (verify = False)
    response = requests.post(
        url,
        json={
            "username": user,
            "password": password
        },
        verify=False
    )
    #server responds with 200, then success. Token string extracted/used in future requests to other endpoints.
    #else print error message
    if response.status_code == 200:
        token = response.text
        print("Authenticated with token: " + token)
    else:
        print(response.text)


#takes device input of type Device/defined in schema
#insert basic info about device (day0) configs
def day0(device: Device):
    #connects to MySQL DB server running on localhost
    # (127.0.0.1), port 3306, etc
    conn = mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="password",
        database="AutoNetOps"
    )

    #cursor object: allows execution of SQL commands
    #insert values into device
    db_cursor = conn.cursor()
    sql = """
    INSERT INTO device (hostname, ip_address, platform, username, password)
    VALUES (%s, %s, %s, %s, %s)
    """
    # tuple of values
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

    
