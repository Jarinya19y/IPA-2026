#!/usr/bin/env python3
import re
from netmiko import ConnectHandler

# SSH Username for the devices
USERNAME = "admin"  # Update with your device username

# Device inventory using SSH Keys
devices = {
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

def main():
    # Regular Expression
    uptime_pattern = re.compile(r"uptime is\s+(.+)", re.IGNORECASE)
   
    # tatus = up และ Protocol = up
    active_intf_pattern = re.compile(r"^(\S+)\s+(\S+)\s+YES\s+\S+\s+up\s+up", re.MULTILINE | re.IGNORECASE)

    for dev_name, dev_info in devices.items():
        print("=" * 55)
        print(f"Device: {dev_name} ({dev_info['host']})")
        print("=" * 55)

        try:
            net_connect = ConnectHandler(**dev_info)

            # --- ตรวจสอบ Uptime จาก show version ---
            version_output = net_connect.send_command("show version")
            uptime_match = uptime_pattern.search(version_output)
            uptime = uptime_match.group(1).strip() if uptime_match else "N/A"
            print(f"System Uptime : {uptime}\n")

            # --- ตรวจสอบ Active Interfaces จาก show ip interface brief ---
            ip_brief_output = net_connect.send_command("show ip interface brief")
            active_interfaces = active_intf_pattern.findall(ip_brief_output)

            print("Active Interfaces (Status: UP / Protocol: UP):")
            if active_interfaces:
                print(f"{'Interface':<25} {'IP Address':<18}")
                print("-" * 45)
                for intf, ip in active_interfaces:
                    print(f"{intf:<25} {ip:<18}")
            else:
                print("  No active interfaces found.")

            net_connect.disconnect()
            print("\n")

        except Exception as e:
            print(f"Error connecting to {dev_name}: {e}\n")

if __name__ == '__main__':
    main()