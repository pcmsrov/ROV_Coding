import socket

server_ip = 'ESP32_IP_ADDRESS'
server_port = 80

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((server_ip, server_port))

request = "GET / HTTP/1.1\r\nHost: {}\r\n\r\n".format(server_ip)
sock.send(request.encode())

with open('depth_data.csv', 'w') as f:
    while True:
        data = sock.recv(1024)
        if not data:
            break
        f.write(data.decode())

sock.close()
