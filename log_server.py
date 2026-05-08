"""
HTTP Chat Log Server - Serves chat history via HTTP
Threaded server on port 8080 that provides /chatlog endpoint.
"""

import socket
import threading
import time
import os
from collections import deque


# Configuration
HOST = "0.0.0.0"
PORT = 8080
MAX_MESSAGES = 50
CHAT_LOG_FILE = "chat_history.log"


class ChatLogServer:
    """HTTP server for chat logs with threading support."""
    
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.chat_messages = deque(maxlen=MAX_MESSAGES)
        self.running = False
        self.server_socket = None
        self.lock = threading.Lock()
        
        # Load existing messages
        self._load_messages()
    
    def _load_messages(self):
        """Load messages from log file."""
        if os.path.exists(CHAT_LOG_FILE):
            try:
                with open(CHAT_LOG_FILE, "r") as f:
                    lines = f.readlines()
                    for line in lines[-MAX_MESSAGES:]:
                        line = line.strip()
                        if line:
                            self.chat_messages.append(line)
            except Exception:
                pass
    
    def add_message(self, message):
        """
        Add a chat message to the log.
        
        Args:
            message: String message to add
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        
        with self.lock:
            self.chat_messages.append(formatted)
            self._save_message(formatted)
    
    def _save_message(self, message):
        """Save a single message to the log file."""
        try:
            with open(CHAT_LOG_FILE, "a") as f:
                f.write(message + "\n")
        except Exception:
            pass
    
    def _build_html_response(self):
        """Build HTML page with chat history."""
        messages_html = ""
        
        with self.lock:
            for msg in self.chat_messages:
                # Escape HTML special characters
                msg_escaped = (msg
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;"))
                messages_html += f'<div class="message">{msg_escaped}</div>'
        
        if not messages_html:
            messages_html = '<div class="message">No messages yet</div>'
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ChatNet Chat Log</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
        }}
        h1 {{
            color: #667eea;
            text-align: center;
            margin-bottom: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 15px;
        }}
        .meta {{
            text-align: center;
            color: #666;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .chat-container {{
            background: #f5f7fa;
            border-radius: 8px;
            padding: 20px;
            max-height: 500px;
            overflow-y: auto;
        }}
        .message {{
            background: white;
            padding: 12px 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            word-wrap: break-word;
        }}
        .message:first-child {{
            border-left-color: #764ba2;
            background: #f8f0ff;
        }}
        .timestamp {{
            color: #999;
            font-size: 12px;
            margin-right: 10px;
        }}
        footer {{
            text-align: center;
            margin-top: 20px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>💬 ChatNet Chat Log</h1>
        <div class="meta">Showing last {min(len(self.chat_messages), MAX_MESSAGES)} messages</div>
        <div class="chat-container">
            {messages_html}
        </div>
        <footer>ChatNet HTTP Log Server</footer>
    </div>
</body>
</html>"""
        return html
    
    def _build_response(self, status_line, content, content_type="text/html"):
        """Build HTTP response."""
        content_bytes = content.encode("utf-8")
        
        response = f"HTTP/1.1 {status_line}\r\n"
        response += f"Content-Type: {content_type}; charset=utf-8\r\n"
        response += f"Content-Length: {len(content_bytes)}\r\n"
        response += "Connection: close\r\n"
        response += "\r\n"
        
        return response.encode("utf-8") + content_bytes
    
    def _parse_http_request(self, data):
        """Parse HTTP request and return (method, path)."""
        try:
            lines = data.decode("utf-8").split("\r\n")
            if not lines:
                return None, None
            
            # Parse request line: GET /path HTTP/1.1
            request_line = lines[0]
            parts = request_line.split(" ")
            
            if len(parts) >= 2:
                method = parts[0]
                path = parts[1]
                return method, path
            
        except Exception:
            pass
        
        return None, None
    
    def _handle_client(self, client_socket, client_addr):
        """Handle HTTP client request."""
        try:
            # Receive request
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = client_socket.recv(1024)
                if not chunk:
                    break
                data += chunk
            
            if not data:
                client_socket.close()
                return
            
            # Parse request
            method, path = self._parse_http_request(data)
            
            # Route handling
            if method == "GET" and path == "/chatlog":
                # Success response
                html = self._build_html_response()
                response = self._build_response("200 OK", html)
            elif path == "/" or path == "":
                # Redirect to /chatlog
                html = '<html><head><meta http-equiv="refresh" content="0;url=/chatlog"></head></html>'
                response = self._build_response("200 OK", html)
            else:
                # 404 Not Found
                html = "<html><body><h1>404 Not Found</h1></body></html>"
                response = self._build_response("404 Not Found", html)
            
            client_socket.sendall(response)
            
        except Exception as e:
            pass
        finally:
            client_socket.close()
    
    def start(self):
        """Start the HTTP server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        print(f"Chat Log Server started on http://0.0.0.0:{self.port}/chatlog")
        print(f"Serving last {MAX_MESSAGES} messages")
        
        while self.running:
            try:
                client_socket, client_addr = self.server_socket.accept()
                # Handle each client in a new thread
                threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_addr)
                ).start()
            except Exception:
                if self.running:
                    continue
                break
    
    def stop(self):
        """Stop the HTTP server."""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass


def get_chat_server():
    """Get the global chat log server instance."""
    global _chat_server
    if '_chat_server' not in globals():
        _chat_server = ChatLogServer()
    return _chat_server


# Global server instance
_chat_server = None


if __name__ == "__main__":
    server = ChatLogServer()
    
    # Add some test messages
    server.add_message("User1: Hello everyone!")
    server.add_message("User2: Hi User1!")
    server.add_message("User3: Welcome to ChatNet!")
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()