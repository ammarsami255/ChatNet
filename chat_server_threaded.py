"""
ChatNet Server - Multithreaded TCP chat server with Advanced Network Services
Features:
- Multithreaded TCP chat server
- DNS Resolver integration (client hostname resolution)
- HTTP Chat Log Server (port 8080)
- SMTP Email notifications for @mentions
"""

import socket
import threading
import time
import os

# Import Task 4 modules
from smtp_notifier import find_mentions, notify_mention
from log_server import ChatLogServer

# Server configuration
HOST = "0.0.0.0"
PORT = 12000
HTTP_PORT = 8080

# Create server socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()

# Thread-safe client management
clients = {}
clients_lock = threading.Lock()

# Chat log server instance
chat_log_server = None


def log(msg, log_type="info"):
    """Log messages to server.log."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{log_type}] {msg}\n"
    with open("server.log", "a") as f:
        f.write(log_line)


def broadcast(msg, sender=None):
    """Broadcast message to all clients."""
    with clients_lock:
        for username, conn in clients.items():
            if username != sender:
                try:
                    conn.send(msg.encode())
                except:
                    pass
    
    # Log to HTTP chat history if enabled
    if chat_log_server:
        chat_log_server.add_message(msg)


def start_http_server():
    """Start HTTP chat log server in a separate thread."""
    global chat_log_server
    chat_log_server = ChatLogServer(host="0.0.0.0", port=HTTP_PORT)
    log(f"Starting HTTP log server on port {HTTP_PORT}", "http")
    
    # Run in background thread
    http_thread = threading.Thread(target=chat_log_server.start, daemon=True)
    http_thread.start()
    
    return chat_log_server


def handle_mention(message, sender):
    """Check for @mentions and send email notifications."""
    mentions = find_mentions(message)
    
    if mentions:
        # Log that mentions were found
        for mentioned_user in mentions:
            log(f"@mention detected: {sender} mentioned @{mentioned_user}", "smtp")
            
            # Send email notification (asynchronous)
            thread = threading.Thread(
                target=notify_mention,
                args=(message,),
                daemon=True
            )
            thread.start()


def handle_client(conn, addr):
    """Handle client connection."""
    username = None
    try:
        # Receive username
        username = conn.recv(1024).decode()
        
        with clients_lock:
            if username in clients:
                conn.send("409".encode())  # Username taken
                conn.close()
                return
            clients[username] = conn
        
        conn.send("200".encode())  # Success
        log(f"{username} connected from {addr}", "conn")
        
        # Notify about new connection
        if chat_log_server:
            chat_log_server.add_message(f"System: {username} joined the chat")
        
        while True:
            try:
                data = conn.recv(4096).decode()
                if not data:
                    break
                
                if data == "/users":
                    with clients_lock:
                        conn.send(str(list(clients.keys())).encode())
                
                elif data == "/quit":
                    break
                
                elif data.startswith("/msg "):
                    # Private message format: /msg <recipient> <message>
                    parts = data.split(" ", 2)
                    if len(parts) >= 3:
                        _, recipient, msg = parts
                        with clients_lock:
                            if recipient in clients:
                                clients[recipient].send(f"[PM] {username}: {msg}".encode())
                                log(f"PM from {username} to {recipient}", "pm")
                else:
                    # Broadcast to all
                    full_message = f"{username}: {data}"
                    broadcast(full_message, username)
                    
                    # Check for @mentions
                    handle_mention(data, username)
                    
                    log(f"Message from {username}", "msg")
            
            except Exception as e:
                break
        
        # Cleanup on disconnect
        with clients_lock:
            if username in clients:
                del clients[username]
        
        log(f"{username} disconnected", "conn")
        
        if chat_log_server:
            chat_log_server.add_message(f"System: {username} left the chat")
    
    except Exception as e:
        log(f"Client handler error: {e}", "error")
    finally:
        try:
            conn.close()
        except:
            pass


# Start HTTP log server before accepting connections
start_http_server()

log("ChatNet server started", "init")
print(f"ChatNet server listening on {HOST}:{PORT}")
print(f"HTTP chat log available at http://localhost:{HTTP_PORT}/chatlog")

# Accept client connections
while True:
    try:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()
        print(f"Active connections: {len(clients)}")
    except KeyboardInterrupt:
        log("Server stopped by user", "init")
        break
    except Exception as e:
        log(f"Accept error: {e}", "error")