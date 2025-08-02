import json
import os

import mysql.connector
import xmltodict
from ncclient import manager
from lxml import etree

from day1 import db_derivation


def get_ospf_config(device_id, filter_xml):
    device = db_derivation(device_id)

    with manager.connect(
        host=device["host"],
        port=device["port"],
        username=device["username"],
        password=device["password"],
        hostkey_verify=False
    ) as m:
        response = m.get_config(source='running', filter=("subtree", filter_xml))
        print(response.xml)
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

            ospf_data = {
                "process_id": process_id,
                "networks": networks,
                "reference_bandwidth": ref_bw
            }

            return ospf_data

        except KeyError:
            print("No OSPF configuration found.")
            return None


def get_all_interface_ips(device_id, filter_xml):
    device = db_derivation(device_id)

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


def routing_info(device_id, filter_xml):
    device = db_derivation(device_id)

    with manager.connect(
            host=device["host"],
            port=device["port"],
            username=device["username"],
            password=device["password"],
            hostkey_verify=False,
            device_params={'name': 'iosxe'}
    ) as m:
        filter_xml = "".join(filter_xml) if isinstance(filter_xml, list) else filter_xml.strip()
        response = m.get(filter=("subtree", filter_xml))
        data = xmltodict.parse(response.xml)
        print(json.dumps(data, indent=2))
        print( data)
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
