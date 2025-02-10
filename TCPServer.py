import socket
import threading
import datetime
import os
from typing import Dict
from threading import Lock  # Import threading lock


class TCPServer:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = 'localhost'
        self.port = 12345
        self.max_clients = 3
        self.clients = [0,0,0]
        self.client_cache: Dict[str, dict] = {}
        self.files_directory = "server_files"
        self.lock = Lock()
        
        # Create files directory if it doesn't exist
        if not os.path.exists(self.files_directory):
            os.makedirs(self.files_directory)
    
    def start_server(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(self.max_clients)
        print(f"Server is listening on {self.host}:{self.port}")
        print(f"Maximum clients allowed: {self.max_clients}")

        try:
            while True:
                client_socket, addr = self.server_socket.accept()
                with self.lock:
                    if not 0 in self.clients:
                        # immediately reject if server is full
                        client_socket.send("Server is full. Please try again later.".encode())
                        client_socket.close()
                        continue
                    
                    #increment if server isnt full
                    self.clients[self.clients.index(0)] = 1
                    #lock no longer needed, 

                 # Start new thread for client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, addr)
                )
                client_thread.start()
                    
        
        except KeyboardInterrupt:
            print("\nServer shutting down...")
        finally:
            self.server_socket.close()

    def handle_client(self, client_socket: socket.socket, addr: tuple):
        try:
            client_socket.send(str(self.clients.index(1)+1).encode()) #send the number of clients currently connected
            client_name = client_socket.recv(1024).decode().strip() #assign name sent by client
            with self.lock:
                self.clients[self.clients.index(1)] = 2
            connection_time = datetime.datetime.now()
            
            # Store client info in cache
            self.client_cache[client_name] = {
                'address': addr,
                'connection_time': connection_time,
                'disconnection_time': None
            }
            
            print(f"Connected: {client_name} from {addr}")
            
            while True:
                data = client_socket.recv(1024).decode().strip()
                if not data:
                    break

                print(f"Received from {client_name}: {data}")

                if data.lower() == 'exit':
                    break
                elif data.lower() == 'status':
                    response = self.get_cache_status()
                    client_socket.send(response.encode())
                elif data.lower() == 'list':
                    response = self.get_file_list()
                    client_socket.send(response.encode())
                elif data.lower().startswith('get '):
                    filename = data[4:].strip()
                    self.send_file(client_socket, filename)
                else:
                    # Echo back with ACK
                    response = f"{data} ACK"
                    client_socket.send(response.encode())

        except Exception as e:
            print(f"Error handling {addr}: {e}")
        
        finally:
            with self.lock: 
                self.clients[int(client_name[-1])-1] = 0

                print(f"Updated client count is: {3-self.clients.count(0)}")

            # Update cache with disconnection time
            if client_name in self.client_cache:
                self.client_cache[client_name]['disconnection_time'] = datetime.datetime.now()

            client_socket.close()
            print(f"Disconnected: {client_name}")

    def get_cache_status(self) -> str:
        status = "=== Server Cache Status ===\n"
        for client, info in self.client_cache.items():
            status += f"\nClient: {client}\n"
            status += f"Address: {info['address']}\n"
            status += f"Connected: {info['connection_time']}\n"
            status += f"Disconnected: {info['disconnection_time'] or 'Still connected'}\n"
        return status

    def get_file_list(self) -> str:
        try:
            files = os.listdir(self.files_directory)
            if not files:
                return "No files available in server repository"
            return "Available files:\n" + "\n".join(files)
        except Exception as e:
            return f"Error accessing files: {e}"

    def send_file(self, client_socket: socket.socket, filename: str):
        file_path = os.path.join(self.files_directory, filename)
        if not os.path.exists(file_path):
            client_socket.send(f"Error: File '{filename}' not found".encode())
            return

        try:
            with open(file_path, 'rb') as file:
                client_socket.send(f"Sending file: {filename}".encode())
                #print("waiting for signal")
                client_socket.recv(1024)  # Wait for client ready signal
                #print("signal got")
                while True:
                    bytes_read = file.read(4096)
                    if not bytes_read:
                        #print("no byte")
                        break
                    client_socket.sendall(bytes_read)
                    # wait for acknowledgment from client
                    client_socket.recv(1024) 
                    #print(f"Sent {len(bytes_read)} bytes...") 

                
                client_socket.send(b"END_OF_FILE")
                print("file sent!")
        except Exception as e:
            client_socket.send(f"Error sending file: {e}".encode())

if __name__ == '__main__':
    server = TCPServer()
    server.start_server()