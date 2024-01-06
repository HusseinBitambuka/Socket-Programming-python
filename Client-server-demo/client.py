# echo-client.py
import socket

HOST = '127.0.0.1' # The server's hostname or IP address
PORT = 65432 # The port used by the server

# Create a socket object
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # Connect to the server
    s.connect((HOST, PORT))
    # Send data to the server
    s.sendall(b'Hello, world')
    # Receive data from the server
    data = s.recv(1024)

print(f'Received: {data.decode()}')