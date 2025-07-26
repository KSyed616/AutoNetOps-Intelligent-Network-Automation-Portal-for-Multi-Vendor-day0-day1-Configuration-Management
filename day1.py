import os
import subprocess
import tempfile
from typing import List

import mysql.connector
import xmltodict
from jinja2 import Environment, FileSystemLoader, meta
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

        all_interfaces = []

        for intf in interfaces:
            name = intf.get("name")
            if name == "GigabitEthernet1":
                continue

            oper_status = intf.get("oper-status", "down")

            status = "Enabled" if oper_status == "up" else "Disabled"

            all_interfaces.append({
                "name": name,
                "status": status
            })

        return all_interfaces


def gen_int_temp(fields: List[str], ipv4_prefix_option: str):
    template_str = """<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
      <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
        <interface>
          <name>{{ name }}</name>
        {% if not is_reconfig %}
          <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
        {% endif %}

    """

    # Append selected fields
    if "description" in fields:
        template_str += "      <description>{{ description }}</description>\n"

    if "enabled" in fields:
        template_str += (
            "        {% if not is_reconfig %}<enabled>{{ enabled }}</enabled>{% endif %}\n"
        )

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

    print(template_str)
    output_dir = "configurations/generated"
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "interface_temp.j2"), "w") as f:
        f.write(template_str)


def get_template_variables(template_path: str):
    env = Environment(loader=FileSystemLoader("/app/configurations/generated"))
    template_source = env.loader.get_source(env, template_path)[0]
    parsed_content = env.parse(template_source)
    return meta.find_undeclared_variables(parsed_content)


def create_temp(template_name, context, is_reconfig):
    env = Environment(loader=FileSystemLoader("/app/configurations/generated"))
    template = env.get_template(template_name)

    context["is_reconfig"] = is_reconfig
    print("is reconfig", is_reconfig)

    xml_string = template.render(context)
    return xml_string


def validate(template_name, context, yang_model_dir: str, module_file: str, is_reconfig: bool):
    xml_string = create_temp(template_name, context, is_reconfig)

    with tempfile.NamedTemporaryFile(mode='w+', suffix=".xml", delete=False) as tmp:
        tmp.write(xml_string)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [
                "pyang",
                "-p", yang_model_dir,
                "-f", "sample-xml-skeleton",
                os.path.join(yang_model_dir, module_file),
                "--sample-xml-skeleton-doctype=config",
                "--sample-xml-skeleton-path", tmp_path
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("XML is valid against YANG model.")
            return True
        else:
            print("Validation failed:\n", result.stderr)
            return False

    finally:
        os.remove(tmp_path)


def push_int(xml_string, device_id):
    device = db_derivation(device_id)
    print("device ", device)

    with manager.connect(
            host=device["host"],
            port=device["port"],
            username=device["username"],
            password=device["password"],
            hostkey_verify=False,
    ) as m:
        response = m.edit_config(
            target='running',
            config=xml_string,
            default_operation='replace')

        print("NETCONF Response:\n", response)
        return response


def get_interface_ip(mgr, interface_name):
    filter_xml = f"""
    <filter>
      <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
        <interface>
          <name>{interface_name}</name>
          <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip"/>
        </interface>
      </interfaces>
    </filter>
    """
    print(filter_xml)

    result = mgr.get_config(source='running', filter=("subtree", filter_xml))
    data = xmltodict.parse(result.xml)
    print("dd", data)


    try:
        ip_info = data["rpc-reply"]["data"]["interfaces"]["interface"]["ipv4"]["address"]
        ip = ip_info["ip"]
        netmask = ip_info["netmask"]
        return ip, netmask
    except KeyError:
        return None, None


def delete_int(device_id, interface_name, ):
    device = db_derivation(device_id)

    with manager.connect(
            host=device["host"],
            port=device["port"],
            username=device["username"],
            password=device["password"],
            hostkey_verify=False
    ) as mgr:
        print("omt", interface_name)
        ip, netmask = get_interface_ip(mgr, interface_name)

        if not ip or not netmask:
            print("No IP config found to delete.")
            return

        delete_config = f"""
           <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
             <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
               <interface>
                 <name>{interface_name}</name>
                 <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip">
                   <address xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0" xc:operation="delete">
                     <ip>{ip}</ip>
                     <netmask>{netmask}</netmask>
                   </address>
                 </ipv4>
               </interface>
             </interfaces>
           </config>
           """

        print(delete_config)
        response = mgr.edit_config(target='running', config=delete_config, default_operation='none')
        print(response)
