import json
import os

import mysql.connector
import xmltodict
from ncclient import manager
from lxml import etree

from day1 import db_derivation


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

    filter_xml = build_routing_filter()  # dynamic generation

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


def build_routing_filter():
    ns = "urn:ietf:params:xml:ns:yang:ietf-routing"
    routing_state = etree.Element("routing-state", xmlns=ns)
    routing_instance = etree.SubElement(routing_state, "routing-instance")
    etree.SubElement(routing_instance, "name")

    ribs = etree.SubElement(routing_instance, "ribs")
    rib = etree.SubElement(ribs, "rib")
    etree.SubElement(rib, "name")

    routes = etree.SubElement(rib, "routes")
    route = etree.SubElement(routes, "route")

    etree.SubElement(route, "destination-prefix")
    etree.SubElement(route, "route-preference")
    etree.SubElement(route, "metric")

    next_hop = etree.SubElement(route, "next-hop")
    etree.SubElement(next_hop, "outgoing-interface")
    etree.SubElement(next_hop, "next-hop-address")

    etree.SubElement(route, "source-protocol")
    etree.SubElement(route, "active")

    return etree.tostring(routing_state).decode()


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
