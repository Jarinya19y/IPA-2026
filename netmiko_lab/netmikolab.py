#!/usr/bin/env python3
import os
from netmiko import ConnectHandler

# SSH Username for the devices
USERNAME = "admin"  # Update with your device username

# Optional: Path to private key if it's not in default ~/.ssh/id_rsa or using ssh-agent
# KEY_FILE = os.path.expanduser("~/.ssh/id_rsa") 

# Device inventory using SSH Keys
devices = {
    'S1': {
        'device_type': 'cisco_ios',
        'host': '172.31.105.3',  
        'username': USERNAME,
        'use_keys': True,        
        'key_file': None,        
    },
    'R1': {
        'device_type': 'cisco_ios',
        'host': '172.31.105.4',
        'username': USERNAME,
        'use_keys': True,
        'key_file': None,
    },
    'R2': {
        'device_type': 'cisco_ios',
        'host': '172.31.105.5',
        'username': USERNAME,
        'use_keys': True,
        'key_file': None,
    },
}

# 1. Switch S1 Configuration (VLAN 101 & VTY Restriction)
s1_config = [
    # Control/Data Plane VLAN setup
    'vlan 101',
    'name CONTROL_DATA_PLANE',
    'exit',
    'interface GigabitEthernet0/1',
    'switchport mode access',
    'switchport access vlan 101',
    'no shutdown',
    'ip access-list extended BLOCK_MGMT_PLANE',
    'deny ip any 172.31.105.0 0.0.0.15',
    'permit ip any any',
    'exit',
    'interface GigabitEthernet1/1',
    'switchport mode access',
    'switchport access vlan 101',
    'ip access-group BLOCK_MGMT_PLANE in',
    'no shutdown',
    # Management Restrict ACL
    'ip access-list standard TELNET_SSH_MGMT',
    'permit 172.31.105.0 0.0.0.15',   # Allow Mgmt Subnet 172.31.105.0/28
    'permit 192.168.1.0 0.0.0.255',
    'exit',
    'line vty 0 15',
    'access-class TELNET_SSH_MGMT in',
    'transport input ssh telnet',
]

# 2. Router R1 Configuration (VRF Aware)
r1_config = [
    'interface GigabitEthernet0/1',
    'ip vrf forwarding Control-data',
    'ip addr 172.31.105.49 255.255.255.240',
    'no shutdown',
    'exit',
    'interface GigabitEthernet0/2',
    'ip vrf forwarding Control-data',
    'ip addr 172.31.105.33 255.255.255.240',
    'no shutdown',
    'exit',
    # OSPF inside CONTROL_DATA VRF
    'router ospf 1 vrf Control-data',
    'router-id 1.1.1.1',
    'network 172.31.105.32 0.0.0.15 area 0',
    'network 172.31.105.48 0.0.0.15 area 0',
    'exit',
    # Management VTY ACL
    'ip access-list standard TELNET_SSH_MGMT',
    'permit 172.31.105.0 0.0.0.15',
    'permit 192.168.1.0 0.0.0.255',
    'exit',
    'line vty 0 4',
    'access-class TELNET_SSH_MGMT in',
    'transport input ssh telnet',
]

# 3. Router R2 Configuration (VRF Aware + PAT + OSPF)
r2_config = [
    'ip access-list extended BLOCK_MGMT_PLANE',
    'deny ip any 172.31.105.0 0.0.0.15',
    'permit ip any any',
    'exit',
    'interface GigabitEthernet0/1',
    'ip vrf forwarding Control-data',
    'ip addr 172.31.105.34 255.255.255.240',
    'no shutdown',
    'exit',
    # Interface towards S1
    'interface GigabitEthernet0/2',
    'ip vrf forwarding Control-data',
    'ip nat inside',
    'ip addr 172.31.105.19 255.255.255.240',
    'ip access-group BLOCK_MGMT_PLANE in',
    'no shutdown',
    'exit',
    # Interface to NAT Cloud
    'interface GigabitEthernet0/3',
    'ip vrf forwarding Control-data,',
    'ip address dhcp',
    'ip nat outside',
    'no shutdown',
    'exit',
    # PAT inside CONTROL_DATA VRF
    'ip access-list standard NAT_ACL',
    'permit 172.31.105.32 0.0.0.15',
    'exit',
    'ip nat inside source list NAT_ACL interface GigabitEthernet0/3 vrf Control-data overload',
    # OSPF in CONTROL_DATA VRF
    'router ospf 1 vrf Control-data',
    'router-id 2.2.2.2',
    'network 172.31.105.16 0.0.0.15 area 0',
    'network 172.31.105.32 0.0.0.15 area 0',
    'passive-interface GigabitEthernet0/3',
    'default-information originate',
    'exit',
    # Static Default Route in VRF towards NAT Cloud
    'ip route vrf Control-data 0.0.0.0 0.0.0.0 GigabitEthernet0/3 dhcp',
    # Management VTY ACL
    'ip access-list standard TELNET_SSH_MGMT',
    'permit 172.31.105.0 0.0.0.15',
    'permit 192.168.1.0 0.0.0.255',
    'exit',
    'line vty 0 4',
    'access-class TELNET_SSH_MGMT in',
    'transport input ssh telnet',
]

config_map = {
    'S1': s1_config,
    'R1': r1_config,
    'R2': r2_config,
}

def main():
    for dev_name, dev_info in devices.items():
        print(f"\n==========================================")
        print(f" Connecting to {dev_name} ({dev_info['host']}) via SSH Key...")
        print(f"==========================================")
        
        try:
            net_connect = ConnectHandler(**dev_info)
            net_connect.enable()
            
            print(f"Applying configs on {dev_name}...")
            output = net_connect.send_config_set(config_map[dev_name])
            print(output)
            
            net_connect.save_config()
            print(f"Saved configuration on {dev_name}.")
            
            net_connect.disconnect()

        except Exception as e:
            print(f"Error connecting to {dev_name}: {e}")

if __name__ == '__main__':
    main()