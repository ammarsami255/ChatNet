"""
SMTP Email Notification Module - sends email notifications for @mentions
Manually implements SMTP protocol over raw TCP socket (no smtplib library).
"""

import socket
import time
import os
import re
import threading


# Configuration - can be overridden via environment variables
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))  # TLS port
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "chatnet@local")
TIMEOUT = 10


class SMTPNotifier:
    """SMTP client using raw TCP socket for sending emails."""
    
    # SMTP response codes
    RESPONSE_READY = "220"
    RESPONSE_OK = "250"
    RESPONSE_START_INPUT = "354"
    RESPONSE_CLOSING = "221"
    
    def __init__(self, smtp_host=None, smtp_port=None, smtp_user=None, 
                 smtp_password=None, smtp_from=None):
        """Initialize SMTP connection parameters."""
        self.smtp_host = smtp_host or SMTP_HOST
        self.smtp_port = smtp_port or SMTP_PORT
        self.smtp_user = smtp_user or SMTP_USER
        self.smtp_password = smtp_password or SMTP_PASSWORD
        self.smtp_from = smtp_from or SMTP_FROM
        self.socket = None
        self.lock = threading.Lock()
    
    def _log(self, message):
        """Log SMTP events."""
        try:
            with open("smtp.log", "a") as f:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass
    
    def _send_command(self, command):
        """Send SMTP command and get response."""
        if self.socket:
            self.socket.sendall(f"{command}\r\n".encode())
            return self._get_response()
        return None
    
    def _get_response(self, timeout=TIMEOUT):
        """Get SMTP server response."""
        if not self.socket:
            return None
        
        self.socket.settimeout(timeout)
        try:
            data = b""
            while b"\r\n" not in data:
                chunk = self.socket.recv(1024)
                if not chunk:
                    return None
                data += chunk
            return data.decode().strip()
        except socket.timeout:
            return None
        except Exception:
            return None
    
    def _parse_response_code(self, response):
        """Extract 3-digit response code from server response."""
        if response and len(response) >= 3:
            return response[:3]
        return None
    
    def connect(self):
        """Connect to SMTP server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(TIMEOUT)
            self.socket.connect((self.smtp_host, self.smtp_port))
            
            # Read welcome message
            response = self._get_response()
            code = self._parse_response_code(response)
            
            if code != self.RESPONSE_READY:
                self._log(f"Connection failed: {response}")
                return False
            
            # EHLO (or HELO for older servers)
            response = self._send_command(f"EHLO localhost")
            if not response or self._parse_response_code(response) != self.RESPONSE_OK:
                # Try HELO
                response = self._send_command(f"HELO localhost")
            
            if not response or self._parse_response_code(response) != self.RESPONSE_OK:
                self._log(f"EHLO failed: {response}")
                return False
            
            # STARTTLS
            response = self._send_command("STARTTLS")
            if response and self._parse_response_code(response) == self.RESPONSE_READY:
                # Upgrade to TLS
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(TIMEOUT)
                self.connect((self.smtp_host, self.smtp_port))
                
                # Re-EHLO after TLS
                self._send_command(f"EHLO localhost")
            
            # AUTH LOGIN
            if self.smtp_user and self.smtp_password:
                response = self._send_command("AUTH LOGIN")
                
                # Send username (base64 encoded)
                import base64
                response = self._send_command(
                    base64.b64encode(self.smtp_user.encode()).decode()
                )
                response = self._send_command(
                    base64.b64encode(self.smtp_password.encode()).decode()
                )
            
            self._log(f"Connected to {self.smtp_host}:{self.smtp_port}")
            return True
            
        except Exception as e:
            self._log(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from SMTP server."""
        try:
            if self.socket:
                self._send_command("QUIT")
                self.socket.close()
                self.socket = None
        except Exception:
            pass
    
    def send_email(self, to_email, subject, body):
        """
        Send an email via SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self.lock:
            result = self._send_email_internal(to_email, subject, body)
            return result
    
    def _send_email_internal(self, to_email, subject, body):
        """Internal method to send email."""
        try:
            # Connect
            if not self.connect():
                return False
            
            # MAIL FROM
            response = self._send_command(f"MAIL FROM:<{self.smtp_from}>")
            if not response or self._parse_response_code(response) != self.RESPONSE_OK:
                self._log(f"MAIL FROM failed: {response}")
                self.disconnect()
                return False
            
            # RCPT TO
            response = self._send_command(f"RCPT TO:<{to_email}>")
            if not response or self._parse_response_code(response) != self.RESPONSE_OK:
                self._log(f"RCPT TO failed: {response}")
                self.disconnect()
                return False
            
            # DATA
            response = self._send_command("DATA")
            if not response or self._parse_response_code(response) != self.RESPONSE_START_INPUT:
                self._log(f"DATA failed: {response}")
                self.disconnect()
                return False
            
            # Build email content
            email_content = (
                f"From: {self.smtp_from}\r\n"
                f"To: {to_email}\r\n"
                f"Subject: {subject}\r\n"
                f"MIME-Version: 1.0\r\n"
                f"Content-Type: text/plain; charset=UTF-8\r\n"
                f"\r\n"
                f"{body}\r\n"
                f".\r\n"
            )
            
            self.socket.sendall(email_content.encode())
            response = self._get_response()
            
            if not response or self._parse_response_code(response) != self.RESPONSE_OK:
                self._log(f"Send failed: {response}")
                self.disconnect()
                return False
            
            self._log(f"Email sent to {to_email}")
            self.disconnect()
            return True
            
        except Exception as e:
            self._log(f"Send error: {e}")
            self.disconnect()
            return False


# Pattern to find @mentions in messages: @username
MENTION_PATTERN = re.compile(r'@(\w+)')


def find_mentions(message):
    """
    Find all @mentions in a message.
    
    Args:
        message: Chat message
        
    Returns:
        list: List of usernames mentioned (without @)
    """
    if not message:
        return []
    return MENTION_PATTERN.findall(message)


# Default global notifier instance
_notifier = None


def get_notifier():
    """Get the global SMTP notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = SMTPNotifier()
    return _notifier


def notify_mention(message, recipient_email=None):
    """
    Send notification when @mention is detected.
    
    Args:
        message: Chat message containing @mention
        recipient_email: Email address to send to (if None, will use mapping)
        
    Returns:
        bool: True if email sent successfully
    """
    mentions = find_mentions(message)
    if not mentions:
        return False
    
    # Get notifier
    notifier = get_notifier()
    
    # If no recipient email provided, use environment variable
    if not recipient_email:
        recipient_email = os.environ.get("CHATNET_TO_EMAIL", "")
    
    if not recipient_email:
        # No email configured
        return False
    
    # Send email
    subject = "ChatNet Mention Alert"
    result = notifier.send_email(recipient_email, subject, message)
    
    return result


if __name__ == "__main__":
    # Test SMTP notifier
    print("Testing SMTP Notifier...")
    
    # Get test email recipient
    to_email = os.environ.get("CHATNET_TO_EMAIL", "")
    
    if not to_email:
        print("Set CHATNET_TO_EMAIL environment variable to test")
        to_email = input("Recipient email: ")
    
    notifier = SMTPNotifier()
    
    # Send test email
    if to_email:
        print(f"Sending test email to {to_email}...")
        result = notifier.send_email(
            to_email,
            "ChatNet Test",
            "This is a test email from ChatNet SMTP Notifier."
        )
        print(f"Email sent: {result}")
    else:
        print("No recipient email specified")