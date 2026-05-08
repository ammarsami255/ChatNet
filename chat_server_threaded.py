import socket
import threading
import time

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("0.0.0.0", 12000))
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
            data = conn.recv(1024).decode()
            if not data:
                break

            if data == "/users":
                conn.send(str(list(clients.keys())).encode())

            elif data.startswith("/msg"):
                _, to, msg = data.split(" ", 2)
                with lock:
                    if to in clients:
                        clients[to].send(f"[PM] {username}: {msg}".encode())

            elif data == "/quit":
                break

            else:
                broadcast(username + ": " + data, username)

        except:
            break

    with lock:
        if username in clients:
            del clients[username]

    log(username + " disconnected")
    conn.close()

while True:
    conn, addr = server.accept()
    threading.Thread(target=handle, args=(conn,)).start()
    print("threads:", threading.active_count())