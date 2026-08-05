#!/usr/bin/env python3
import logging
from jinja2 import Template
from netmiko import ConnectHandler

# Setup logging to see Netmiko output if needed
logging.basicConfig(filename="netmiko.log", level=logging.DEBUG)

USERNAME = "admin"

# ==========================================
# 1. JINJA2 TEMPLATES
# ==========================================

SWITCH_TEMPLATE = """
vlan {{ vlan.id }}
 name {{ vlan.name }}
exit

{% for intf in interfaces %}
interface {{ intf.name }}
 switchport mode access
 switchport access vlan {{ intf.vlan }}
 {% if intf.acl_in %}
 ip access-group {{ intf.acl_in }} in
 {% endif %}
 no shutdown
{% endfor %}

{% if extended_acls %}
{% for acl in extended_acls %}
ip access-list extended {{ acl.name }}
 {% for rule in acl.rules %}
 {{ rule }}
 {% endfor %}
exit
{% endfor %}
{% endif %}

ip access-list standard {{ mgmt_acl.name }}
 {% for permit in mgmt_acl.permits %}
 permit {{ permit }}
 {% endfor %}
exit

line vty 0 {{ vty_range }}
 access-class {{ mgmt_acl.name }} in
 transport input ssh telnet
"""

ROUTER_TEMPLATE = """
{% if extended_acls %}
{% for acl in extended_acls %}
ip access-list extended {{ acl.name }}
 {% for rule in acl.rules %}
 {{ rule }}
 {% endfor %}
exit
{% endfor %}
{% endif %}

{% for intf in interfaces %}
interface {{ intf.name }}
 {% if intf.vrf %}
 ip vrf forwarding {{ intf.vrf }}
 {% endif %}
 {% if intf.nat %}
 ip nat {{ intf.nat }}
 {% endif %}
 {% if intf.ip == 'dhcp' %}
 ip address dhcp
 {% else %}
 ip address {{ intf.ip }} {{ intf.mask }}
 {% endif %}
 {% if intf.acl_in %}
 ip access-group {{ intf.acl_in }} in
 {% endif %}
 no shutdown
exit
{% endfor %}

{% if nat_config %}
ip access-list standard {{ nat_config.acl_name }}
 permit {{ nat_config.source_subnet }} {{ nat_config.wildcard }}
exit
ip nat inside source list {{ nat_config.acl_name }} interface {{ nat_config.interface }} vrf {{ nat_config.vrf }} overload
{% endif %}

{% if ospf %}
router ospf {{ ospf.process_id }} vrf {{ ospf.vrf }}
 router-id {{ ospf.router_id }}
 {% for net in ospf.networks %}
 network {{ net.subnet }} {{ net.wildcard }} area {{ net.area }}
 {% endfor %}
 {% if ospf.passive_interface %}
 passive-interface {{ ospf.passive_interface }}
 {% endif %}
 {% if ospf.default_information_originate %}
 default-information originate
 {% endif %}
exit
{% endif %}

{% if static_routes %}
{% for route in static_routes %}
ip route vrf {{ route.vrf }} {{ route.prefix }} {{ route.mask }} {{ route.next_hop }}
{% endfor %}
{% endif %}

ip access-list standard {{ mgmt_acl.name }}
 {% for permit in mgmt_acl.permits %}
 permit {{ permit }}
 {% endfor %}
exit

line vty 0 {{ vty_range }}
 access-class {{ mgmt_acl.name }} in
 transport input ssh telnet
"""

# Common Management ACL shared across all devices
MGMT_ACL_DATA = {
    "name": "TELNET_SSH_MGMT",
    "permits": [
        "172.31.105.0 0.0.0.15",
        "192.168.1.0 0.0.0.255",
        "10.30.6.0 0.0.0.255",
    ],
}

BLOCK_MGMT_ACL_DATA = {
    "name": "BLOCK_MGMT_PLANE",
    "rules": [
        "deny ip any 172.31.105.0 0.0.0.15",
        "permit ip any any",
    ],
}

# ==========================================
# 2. INVENTORY & DATA MODEL
# ==========================================

devices = {
    "S1": {
        "conn_info": {
            "device_type": "cisco_ios",
            "host": "172.31.105.3",
            "username": USERNAME,
            "use_keys": True,
        },
        "template": SWITCH_TEMPLATE,
        "data": {
            "vlan": {"id": 101, "name": "CONTROL_DATA_PLANE"},
            "interfaces": [
                {"name": "GigabitEthernet0/1", "vlan": 101, "acl_in": None},
                {
                    "name": "GigabitEthernet1/1",
                    "vlan": 101,
                    "acl_in": "BLOCK_MGMT_PLANE",
                },
            ],
            "extended_acls": [BLOCK_MGMT_ACL_DATA],
            "mgmt_acl": MGMT_ACL_DATA,
            "vty_range": "15",
        },
    },
    "R1": {
        "conn_info": {
            "device_type": "cisco_ios",
            "host": "172.31.105.4",
            "username": USERNAME,
            "use_keys": True,
        },
        "template": ROUTER_TEMPLATE,
        "data": {
            "interfaces": [
                {
                    "name": "GigabitEthernet0/1",
                    "vrf": "Control-data",
                    "ip": "172.31.105.49",
                    "mask": "255.255.255.240",
                },
                {
                    "name": "GigabitEthernet0/2",
                    "vrf": "Control-data",
                    "ip": "172.31.105.33",
                    "mask": "255.255.255.240",
                },
            ],
            "ospf": {
                "process_id": 1,
                "vrf": "Control-data",
                "router_id": "1.1.1.1",
                "networks": [
                    {
                        "subnet": "172.31.105.32",
                        "wildcard": "0.0.0.15",
                        "area": 0,
                    },
                    {
                        "subnet": "172.31.105.48",
                        "wildcard": "0.0.0.15",
                        "area": 0,
                    },
                ],
            },
            "mgmt_acl": MGMT_ACL_DATA,
            "vty_range": "4",
        },
    },
    "R2": {
        "conn_info": {
            "device_type": "cisco_ios",
            "host": "172.31.105.5",
            "username": USERNAME,
            "use_keys": True,
        },
        "template": ROUTER_TEMPLATE,
        "data": {
            "extended_acls": [BLOCK_MGMT_ACL_DATA],
            "interfaces": [
                {
                    "name": "GigabitEthernet0/1",
                    "vrf": "Control-data",
                    "ip": "172.31.105.34",
                    "mask": "255.255.255.240",
                },
                {
                    "name": "GigabitEthernet0/2",
                    "vrf": "Control-data",
                    "ip": "172.31.105.19",
                    "mask": "255.255.255.240",
                    "nat": "inside",
                    "acl_in": "BLOCK_MGMT_PLANE",
                },
                {
                    "name": "GigabitEthernet0/3",
                    "vrf": "Control-data",
                    "ip": "dhcp",
                    "nat": "outside",
                },
            ],
            "nat_config": {
                "acl_name": "NAT_ACL",
                "source_subnet": "172.31.105.16",
                "wildcard": "0.0.0.15",
                "interface": "GigabitEthernet0/3",
                "vrf": "Control-data",
            },
            "ospf": {
                "process_id": 1,
                "vrf": "Control-data",
                "router_id": "2.2.2.2",
                "networks": [
                    {
                        "subnet": "172.31.105.16",
                        "wildcard": "0.0.0.15",
                        "area": 0,
                    },
                    {
                        "subnet": "172.31.105.32",
                        "wildcard": "0.0.0.15",
                        "area": 0,
                    },
                ],
                "passive_interface": "GigabitEthernet0/3",
                "default_information_originate": True,
            },
            "static_routes": [
                {
                    "vrf": "Control-data",
                    "prefix": "0.0.0.0",
                    "mask": "0.0.0.0",
                    "next_hop": "GigabitEthernet0/3 dhcp",
                }
            ],
            "mgmt_acl": MGMT_ACL_DATA,
            "vty_range": "4",
        },
    },
}

# ==========================================
# 3. MAIN EXECUTION
# ==========================================


def render_config(template_str, context_data):
    """Renders Jinja2 template and returns a list of commands."""
    template = Template(template_str)
    rendered_text = template.render(context_data)

    # Split lines, remove empty/whitespace-only lines
    config_commands = [
        line.strip() for line in rendered_text.splitlines() if line.strip()
    ]
    return config_commands


def main():
    for dev_name, dev_spec in devices.items():
        print(f"\n{'='*42}")
        print(
            f" Connecting to {dev_name} ({dev_spec['conn_info']['host']}) via SSH Key..."
        )
        print(f"{'='*42}")

        # Render configuration using Jinja2
        commands_to_send = render_config(
            dev_spec["template"], dev_spec["data"]
        )

        try:
            net_connect = ConnectHandler(**dev_spec["conn_info"])
            net_connect.enable()

            print(f"Applying configs on {dev_name}...")
            output = net_connect.send_config_set(commands_to_send)
            print(output)

            net_connect.save_config()
            print(f"Successfully saved configuration on {dev_name}.")

            net_connect.disconnect()

        except Exception as e:
            print(f"Error connecting to or configuring {dev_name}: {e}")


if __name__ == "__main__":
    main()