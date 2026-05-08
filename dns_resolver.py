"""
DNS Resolver Module - UDP-based DNS resolution without OS resolver
Resolves hostnames to IPv4 addresses using raw DNS queries.
"""

import socket
import struct
import random


class DNSResolver:
    """DNS Resolver using UDP socket for A record queries."""
    
    DNS_SERVERS = ["8.8.8.8", "8.8.4.4"]  # Google DNS primary and secondary
    DNS_PORT = 53
    TIMEOUT = 5
    
    def __init__(self, dns_servers=None):
        """Initialize with optional custom DNS servers list."""
        if dns_servers:
            self.dns_servers = dns_servers
        else:
            self.dns_servers = self.DNS_SERVERS
    
    def _build_query(self, hostname):
        """
        Build a raw DNS query packet for A record.
        
        DNS header format:
        - ID (2 bytes): Transaction ID
        - Flags (2 bytes): Standard query
        - QDCOUNT (2 bytes): Number of questions
        - ANCOUNT (2 bytes): Number of answer records
        - NSCOUNT (2 bytes): Number of authority records
        - ARCOUNT (2 bytes): Number of additional records
        
        Question format:
        - QNAME: Domain name in labels (each label: length + content)
        - QTYPE (2 bytes): Query type (1 = A record)
        - QCLASS (2 bytes): Query class (1 = IN)
        """
        # Generate random transaction ID
        transaction_id = random.randint(0, 65535)
        
        # Header: ID (0x0100 = standard query)
        # Flags: 0x0100 (RD flag set)
        # Counts: 1 question, 0 answers, 0 authority, 0 additional
        header = struct.pack("!HHHHHH",
            transaction_id,      # ID
            0x0100,              # Flags (standard query)
            1,                   # QDCOUNT (1 question)
            0,                   # ANCOUNT
            0,                   # NSCOUNT
            0                    # ARCOUNT
        )
        
        # Build QNAME: convert hostname to labels
        qname = b""
        for label in hostname.split("."):
            if label:  # Skip empty labels
                qname += struct.pack("B", len(label)) + label.encode()
        qname += b"\x00"  # Null terminator
        
        # Question: QNAME + QTYPE (1 for A) + QCLASS (1 for IN)
        question = qname + struct.pack("!HH", 1, 1)
        
        return header + question
    
    def _parse_response(self, data):
        """
        Parse binary DNS response and extract A record (IPv4 address).
        
        Returns:
            str: IPv4 address or None if not found
        """
        if len(data) < 12:
            return None
        
        # Parse header
        _, flags, qdcount, ancount, _, _ = struct.unpack("!HHHHHH", data[:12])
        
        # Check if response is valid
        if (flags & 0x8000) == 0:  # Not a response
            return None
        
        if (flags & 0x000F) != 0:  # Error in response
            return None
        
        # Skip question section
        offset = 12
        while offset < len(data):
            # Skip QNAME (read labels)
            while offset < len(data) and data[offset] != 0:
                label_len = data[offset]
                offset += label_len + 1
            offset += 1  # Skip null terminator
            offset += 4  # Skip QTYPE and QCLASS (2 + 2 bytes)
        
        # Parse answer records
        while offset < len(data) and ancount > 0:
            # Skip name (could be pointer or inline)
            if (data[offset] & 0xC0) == 0xC0:
                offset += 2  # Pointer
            else:
                while offset < len(data) and data[offset] != 0:
                    label_len = data[offset]
                    offset += label_len + 1
                offset += 1
            
            # Read record type and class
            if offset + 6 > len(data):
                break
                
            qtype, qclass, ttl, rdlength = struct.unpack("!HHIH", data[offset:offset+10])
            offset += 10
            
            # Check for A record (type 1)
            if qtype == 1 and rdlength == 4:
                # Extract IPv4 address
                ip = socket.inet_ntoa(data[offset:offset+4])
                return ip
            
            offset += rdlength
            ancount -= 1
        
        return None
    
    def resolve(self, hostname):
        """
        Resolve hostname to IPv4 address using DNS servers.
        
        Args:
            hostname: Domain name to resolve
            
        Returns:
            str: IPv4 address or None if resolution failed
        """
        # Remove trailing dot if present
        hostname = hostname.rstrip(".")
        
        query = self._build_query(hostname)
        
        for dns_server in self.dns_servers:
            try:
                # Create UDP socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(self.TIMEOUT)
                
                # Send query
                sock.sendto(query, (dns_server, self.DNS_PORT))
                
                # Receive response
                data, _ = sock.recvfrom(512)
                sock.close()
                
                # Parse response
                ip = self._parse_response(data)
                if ip:
                    return ip
                    
            except Exception as e:
                if sock:
                    sock.close()
                continue
        
        return None


def resolve_hostname(hostname):
    """
    Convenience function to resolve hostname.
    
    Args:
        hostname: Domain name to resolve
        
    Returns:
        str: IPv4 address or None
    """
    resolver = DNSResolver()
    return resolver.resolve(hostname)


if __name__ == "__main__":
    import sys
    
    # Default hostname to resolve
    hostname = sys.argv[1] if len(sys.argv) > 1 else "chatnet.local"
    
    print(f"Resolving {hostname}...")
    
    resolver = DNSResolver()
    ip = resolver.resolve(hostname)
    
    if ip:
        print(f"Resolved {hostname} → {ip}")
    else:
        print(f"Failed to resolve {hostname}")