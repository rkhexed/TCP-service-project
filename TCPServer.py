import socket
import threading
import datetime
import os
from typing import Dict
from threading import Lock  # Import threading lock

class TCPServer:
    """
    A simple multi-client TCP server that handles requests, stores client data,
    and allows file sharing.
    """
    def __init__(self):
        """Initialize server configurations and client handling structures."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = 'localhost'
        self.port = 12345
        self.max_clients = 3  # Maximum number of clients allowed
        self.clients = [0, 0, 0]  # Keeps track of active client slots
        self.client_cache: Dict[str, dict] = {}  # Stores client session data
        self.files_directory = "server_files"  # Directory containing server files
        self.lock = Lock()  # Ensures thread safety for shared resources
        
        # Create the files directory if it doesn't exist
        if not os.path.exists(self.files_directory):
            os.makedirs(self.files_directory)
    
    def start_server(self):
        """Start the server and listen for incoming client connections."""
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(self.max_clients)
        print(f"Server is listening on {self.host}:{self.port}")
        print(f"Maximum clients allowed: {self.max_clients}")

        try:
            while True:
                client_socket, addr = self.server_socket.accept()
                with self.lock:
                    if 0 not in self.clients:
                        # Reject connection if server is full
                        client_socket.send("Server is full. Please try again later.".encode())
                        client_socket.close()
                        continue
                    
                    # Assign a slot to the new client
                    self.clients[self.clients.index(0)] = 1
                
                # Start a new thread to handle client communication
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
        """Handle communication with an individual client."""
        try:
            client_socket.send(str(self.clients.index(1) + 1).encode())  # Assign client number
            client_name = client_socket.recv(1024).decode().strip()  # Receive client name
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
                    # Echo back with acknowledgment
                    response = f"{data} ACK"
                    client_socket.send(response.encode())
        except Exception as e:
            print(f"Error handling {addr}: {e}")
        
        finally:
            with self.lock: 
                self.clients[int(client_name[-1]) - 1] = 0
                print(f"Updated client count is: {3 - self.clients.count(0)}")

            # Update cache with disconnection time
            if client_name in self.client_cache:
                self.client_cache[client_name]['disconnection_time'] = datetime.datetime.now()

            client_socket.close()
            print(f"Disconnected: {client_name}")

    def get_cache_status(self) -> str:
        """Return the current status of connected clients."""
        status = "=== Server Cache Status ===\n"
        for client, info in self.client_cache.items():
            status += f"\nClient: {client}\n"
            status += f"Address: {info['address']}\n"
            status += f"Connected: {info['connection_time']}\n"
            status += f"Disconnected: {info['disconnection_time'] or 'Still connected'}\n"
        return status

    def get_file_list(self) -> str:
        """Retrieve the list of available files on the server."""
        try:
            files = os.listdir(self.files_directory)
            if not files:
                return "No files available in server repository"
            return "Available files:\n" + "\n".join(files)
        except Exception as e:
            return f"Error accessing files: {e}"

    def send_file(self, client_socket: socket.socket, filename: str):
        """Send a requested file to the client."""
        file_path = os.path.join(self.files_directory, filename)
        if not os.path.exists(file_path):
            client_socket.send(f"Error: File '{filename}' not found".encode())
            return
        try:
            with open(file_path, 'rb') as file:
                client_socket.send(f"Sending file: {filename}".encode())
                client_socket.recv(1024)  # Wait for client ready signal
                while True:
                    bytes_read = file.read(4096)
                    if not bytes_read:
                        break
                    client_socket.sendall(bytes_read)
                    client_socket.recv(1024)  # Wait for acknowledgment from client
   
                client_socket.send(b"END_OF_FILE")
                print("File sent successfully!")
        except Exception as e:
            client_socket.send(f"Error sending file: {e}".encode())

if __name__ == '__main__':
    server = TCPServer()
    server.start_server()
