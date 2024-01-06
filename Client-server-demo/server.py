# echo-server.py
import socket

HOST = '127.0.0.1' # Standard loopback interface address (localhost)
PORT = 65432 # Port to listen on (non-privileged ports are > 1023)

# Create a socket object
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # Bind the socket to the address and port
    s.bind((HOST, PORT))
    # Listen for connections
    s.listen()
    # Accept a connection
    conn, addr = s.accept()
    # Print the address of the client
    print('Connected by', addr)
    # Receive data from the client
    with conn:
        while True:
            data = conn.recv(1024)
            # If there is no data, break out of the loop
            if not data:
                break
            # Send the data back to the client
            conn.sendall(data)