"""ChatNet Server with Task 4 features"""

import socket
import threading
import time

from smtp_notifier import notify
import log_server

HOST = "0.0.0.0"
PORT = 12000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()

clients = {}
lock = threading.Lock()

def log(msg):
    with open("server.log", "a") as f:
        f.write(time.ctime() + " " + msg + "\n")

def broadcast(msg, sender=None):
    with lock:
        for u, c in clients.items():
            if u != sender:
                try:
                    c.send(msg.encode())
                except:
                    pass
    log_server.add_message(msg)

def handle(conn):
    username = conn.recv(1024).decode()
    with lock:
        if username in clients:
            conn.send("409".encode())
            conn.close()
            return
        clients[username] = conn
    
    conn.send("200".encode())
    log(username + " connected")
    
    while True:
        try:
            data = conn.recv(4096).decode()
            if not data:
                break
            if data == "/users":
                conn.send(str(list(clients.keys())).encode())
            elif data == "/quit":
                break
            else:
                full = username + ": " + data
                broadcast(full, username)
                notify(full)
                log(full)
        except:
            break
    
    with lock:
        if username in clients:
            del clients[username]
    log(username + " disconnected")
    conn.close()

threading.Thread(target=log_server.start, daemon=True).start()

print(f"ChatNet server on {HOST}:{PORT}")
print(f"Chat log: http://localhost:8080/chatlog")

while True:
    conn, addr = server.accept()
    threading.Thread(target=handle, args=(conn,)).start()