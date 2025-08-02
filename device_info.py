import importlib
import json
import os
import subprocess
import sys

import pyangbind.lib.pybindJSON as pybindJSON
import xmltodict
from ncclient import manager
from lxml import etree

from day1 import db_derivation


def generate_model_binding(model_name: str, yang_dir: str = "models", output_dir: str = "bindings"):
    yang_file = f"{yang_dir}/{model_name}.yang"
    output_file = f"{output_dir}/{model_name.replace('-', '_')}.py"
    module_name = model_name.replace("-", "_")

    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Find pyangbind plugin directory
    result = subprocess.run(
        ["python", "-c", "import pyangbind; print(pyangbind.plugin.__path__[0])"],
        capture_output=True,
        text=True
    )
    plugin_path = result.stdout.strip()

    # Step 2: Generate the binding
    subprocess.run([
        "pyang",
        "--plugindir", plugin_path,
        "-f", "pybind",
        "-o", output_file,
        yang_file
    ], check=True)

    # Step 3: Dynamically import the generated Python module
    spec = importlib.util.spec_from_file_location(module_name, output_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    # Step 4: Return the top-level model class (usually same as file name)
    class_name = module_name  # pyangbind uses same name for class
    model_class = getattr(module, class_name)
    return model_class


def get_ospf_config(device_id):
    device = db_derivation(device_id)

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
            ospf = native_config['router']['router-ospf']['ospf']

            process_id = ospf['process-id']['id']
            networks = ospf['process-id'].get('network', [])
            if isinstance(networks, dict):
                networks = [networks]

            extra_ospf = native_config['router'].get('ospf', {})
            ref_bw = extra_ospf.get('auto-cost', {}).get('reference-bandwidth', 'N/A')
            spf_timers = extra_ospf.get('timers', {}).get('throttle', {}).get('spf', {})

            ospf_data = {
                "process_id": process_id,
                "networks": networks,
                "reference_bandwidth": ref_bw,
                "spf_timers": {
                    "delay": spf_timers.get("delay", "N/A"),
                    "min_delay": spf_timers.get("min-delay", "N/A"),
                    "max_delay": spf_timers.get("max-delay", "N/A")
                }
            }

            return ospf_data

        except KeyError:
            print("No OSPF configuration found.")
            return None


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


def routing_info(device_id):
    device = db_derivation(device_id)

    # Step 1: Build model using pyangbind
    model = generate_model_binding("ietf-routing")

    # Optional: Create routing-instance and RIB filter fields
    ri = model.routing_instance.add("default")
    rib = ri.ribs.rib.add("ipv4-default")

    # Optionally, leave route details blank to pull all
    route = rib.routes.route.add("0.0.0.0/0")

    # Step 2: Convert model -> JSON -> Dict -> XML string
    json_data = pybindJSON.dumps(model, mode="ietf")
    xml_dict = json.loads(json_data)
    filter_xml = xmltodict.unparse({"routing-state": xml_dict["routing-state"]}, pretty=True)

    with manager.connect(
            host=device["host"],
            port=device["port"],
            username=device["username"],
            password=device["password"],
            hostkey_verify=False,
            device_params={'name': 'iosxe'}
    ) as m:
        response = m.get(filter=("subtree", filter_xml))
        data = xmltodict.parse(response.xml)
        print(json.dumps(data, indent=2))
        routes = parse_routes(data)
        return routes


def parse_routes(data):
    routes = []

    rib_data = data['rpc-reply']['data']['routing-state']['routing-instance']
    for instance in rib_data:
        if 'ribs' not in instance:
            continue
        for rib in instance['ribs']['rib']:
            if 'routes' not in rib or 'route' not in rib['routes']:
                continue
            route_entries = rib['routes']['route']
            if isinstance(route_entries, dict):
                route_entries = [route_entries]

            for route in route_entries:
                routes.append({
                    "prefix": route.get("destination-prefix", "N/A"),
                    "protocol": (
                        route.get("source-protocol", {}).get("#text")
                        if isinstance(route.get("source-protocol"), dict)
                        else route.get("source-protocol", "N/A")
                    ),
                    "metric": route.get("metric", "N/A"),
                    "preference": route.get("route-preference", "N/A"),
                    "nexthop": route.get("next-hop", {}).get("next-hop-address", "N/A"),
                    "interface": route.get("next-hop", {}).get("outgoing-interface", "N/A"),
                })
    return routes
