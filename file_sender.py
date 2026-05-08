import socket
import os

def send_file(filename, ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3)

    f = open(filename, "rb")
    seq = 0

    while True:
        data = f.read(512)
        if not data:
            break

        packet = str(seq).encode() + b"|" + data

        while True:
            sock.sendto(packet, (ip, port))

            try:
                ack, _ = sock.recvfrom(1024)
                if ack.decode() == str(seq):
                    print(f"{seq} ACK")
                    break
            except:
                print(f"{seq} timeout retry")

        seq += 1

    f.close()
    sock.sendto(b"END", (ip, port))