import socket
import threading
from file_sender import send_file
from dns_resolver import resolve_hostname

server_ip = input("Server IP or Hostname: ")

# Resolve hostname if not an IP address
if not server_ip.replace(".", "").isdigit():
    print(f"Resolving hostname: {server_ip}")
    resolved_ip = resolve_hostname(server_ip)
    if resolved_ip:
        print(f"Resolved {server_ip} → {resolved_ip}")
        server_ip = resolved_ip
    else:
        print("DNS resolution failed, trying as-is")

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((server_ip, 12000))

username = input("Username: ")
client.send(username.encode())

if client.recv(1024).decode() == "409":
    print("Username taken")
    exit()

def receive():
    while True:
        try:
            print(client.recv(1024).decode())
        except:
            break

def send():
    while True:
        msg = input()

        if msg.startswith("/sendfile"):
            parts = msg.split(" ")
            if len(parts) == 3:
                filename = parts[1]

                threading.Thread(
                    target=send_file,
                    args=(filename, server_ip, 5000)
                ).start()

            continue

        client.send(msg.encode())

        if msg == "/quit":
            break

threading.Thread(target=receive).start()
send()
client.close()