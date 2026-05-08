"""HTTP Chat Log Server - port 8080"""

import socket
import threading
from collections import deque

PORT = 8888
MAX = 50
messages = deque(maxlen=MAX)

def add_message(msg):
    messages.append(msg)

def html():
    m = "".join(f"<p>{x}</p>" for x in messages)
    return f"""HTTP/1.1 200 OK
Content-Type: text/html

<html><body><h1>ChatNet Chat Log</h1>{m}</body></html>"""

def handle(s):
    try:
        data = s.recv(1024)
        if b"GET /chatlog" in data:
            s.sendall(html().encode())
        else:
            s.sendall(b"HTTP/1.1 404 Not Found\n\n404")
    except:
        pass
    finally:
        s.close()

def start():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(("0.0.0.0", PORT))
    except OSError as e:
        print(f"HTTP server failed: {e}")
        return
    server.listen(5)
    print(f"HTTP server on port {PORT}")
    while True:
        c, _ = server.accept()
        threading.Thread(target=handle, args=(c,)).start()

if __name__ == "__main__":
    start()