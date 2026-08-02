import paramiko
import time


ROUTER_IPS = ["172.31.105.1", "172.31.105.4", "172.31.105.5", "172.31.105.2", "172.31.105.3"]  
USERNAME = "admin"
KEY_FILE_PATH = "/home/devasc/.ssh/id_rsa"


def get_running_config(ip):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        
        private_key = paramiko.RSAKey.from_private_key_file(KEY_FILE_PATH)

        print(f"\n==========================================")
        print(f"Connecting to {ip}...")
        
        client.connect(
            hostname=ip,
            username=USERNAME,
            pkey=private_key,
            timeout=10,
            look_for_keys=False,
            allow_agent=False
        )
        print(f"Successfully authenticated to {ip}!")

        
        shell = client.invoke_shell()
        shell.send("terminal length 0\n")
        time.sleep(1)

        if shell.recv_ready():
            shell.recv(65535)

        print(f"Fetching running-config from {ip}...")
        shell.send("show running-config\n")
        time.sleep(3)


        output = ""
        while shell.recv_ready():
            output += shell.recv(65535).decode('utf-8', errors='ignore')
            time.sleep(0.5)


        filename = f"running_config_{ip}.txt"
        with open(filename, "w") as config_file:
            config_file.write(output)
        print(f"Saved running configuration to '{filename}'")

        shell.send("exit\n")
        time.sleep(0.5)

    except paramiko.AuthenticationException:
        print(f"[{ip}] Authentication failed! Check SSH key.")
    except paramiko.SSHException as ssh_err:
        print(f"[{ip}] SSH connection error: {ssh_err}")
    except Exception as e:
        print(f"[{ip}] Error: {e}")
    finally:
        client.close()
        print(f"Closed connection to {ip}.")


if __name__ == "__main__":
    for ip in ROUTER_IPS:
        get_running_config(ip)