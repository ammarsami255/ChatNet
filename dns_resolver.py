"""DNS Resolver - UDP-based hostname resolution"""

import socket
import struct

def resolve(hostname, dns_server="8.8.8.8", port=53):
    """Resolve hostname using UDP DNS query."""
    # Build DNS query
    tid = 1234
    query = struct.pack("!HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    for label in hostname.split("."):
        query += struct.pack("B", len(label)) + label.encode()
    query += b"\x00\x00\x01\x00\x01"
    
    # Send UDP request
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    sock.sendto(query, (dns_server, port))
    data, _ = sock.recvfrom(512)
    sock.close()
    
    # Parse A record
    offset = 12
    while offset < len(data) and data[offset] != 0:
        offset += data[offset] + 1
    offset += 13
    
    if offset + 4 <= len(data):
        return socket.inet_ntoa(data[offset:offset+4])
    return None

if __name__ == "__main__":
    import sys
    h = sys.argv[1] if len(sys.argv) > 1 else "chatnet.local"
    r = resolve(h)
    if r:
        print(f"Resolved {h} → {r}")
    else:
        print(f"Failed to resolve {h}")