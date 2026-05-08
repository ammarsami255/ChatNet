"""SMTP Notifier - raw TCP email"""

import socket
import os
import re

# Configure via env vars
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
FROM_ADDR = os.environ.get("SMTP_FROM", "chatnet@local")
TO_ADDR = os.environ.get("SMTP_TO", "")

def send(to_email, subject, body):
    """Send email via raw TCP SMTP."""
    if not to_email:
        to_email = TO_ADDR
    if not to_email:
        return False
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect((SMTP_HOST, SMTP_PORT))
    s.recv(1024)  # 220
    
    s.send(b"EHLO localhost\r\n")
    s.recv(1024)  # 250
    
    s.send(b"STARTTLS\r\n")
    s.recv(1024)  # 220
    
    s.send(b"EHLO localhost\r\n")
    s.recv(1024)
    
    if SMTP_USER and SMTP_PASS:
        import base64
        s.send(b"AUTH LOGIN\r\n")
        s.recv(1024)
        s.send(base64.b64encode(SMTP_USER.encode()) + b"\r\n")
        s.recv(1024)
        s.send(base64.b64encode(SMTP_PASS.encode()) + b"\r\n")
        s.recv(1024)
    
    s.send(f"MAIL FROM:<{FROM_ADDR}>\r\n".encode())
    s.recv(1024)
    
    s.send(f"RCPT TO:<{to_email}>\r\n".encode())
    s.recv(1024)
    
    s.send(b"DATA\r\n")
    s.recv(1024)
    
    msg = f"From: {FROM_ADDR}\r\nTo: {to_email}\r\nSubject: {subject}\r\n\r\n{body}\r\n.\r\n"
    s.send(msg.encode())
    s.recv(1024)
    
    s.send(b"QUIT\r\n")
    s.close()
    return True

def find_mentions(msg):
    """Find @username mentions."""
    return re.findall(r"@(\w+)", msg)

def notify(msg):
    """Notify on @mention."""
    if find_mentions(msg):
        return send(TO_ADDR, "ChatNet Mention Alert", msg)
    return False

if __name__ == "__main__":
    print("SMTP module ready")