import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 5000))

file = open("received_file", "wb")

while True:
    data, addr = sock.recvfrom(1024)

    if data == b"END":
        break

    seq, content = data.split(b"|", 1)

    file.write(content)

    sock.sendto(seq, addr)

file.close()
print("File received successfully")