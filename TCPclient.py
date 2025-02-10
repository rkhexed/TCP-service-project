import socket
import os
import threading

class TCPClient:
    """
    A simple TCP client that connects to a server, sends messages, receives responses,
    and downloads files from the server.
    """
    def __init__(self):
        """Initialize the client socket and set up configurations."""
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = 'localhost'  # Server address
        self.port = 12345        # Server port
        self.client_name = None
        self.downloads_folder = "client_downloads"
        self.locked = False  # Prevents concurrent message sending while downloading
        
        # Create downloads folder if it doesn't exist
        if not os.path.exists(self.downloads_folder):
            os.makedirs(self.downloads_folder)

    def start_client(self):
        """Attempt to connect to the server and initiate communication."""
        try:
            self.client_socket.connect((self.host, self.port))
            
            # Get client name from server and acknowledge
            self.send_client_name()
            
            # Start a separate thread for receiving messages from the server
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()

            # Display available commands
            self.print_help()
            
            # Main sending loop
            self.send_messages()
            
        except ConnectionRefusedError:
            print("Failed to connect to server. Make sure the server is running.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.client_socket.close()

    def send_client_name(self):
        """Receive client number from the server and send back a unique client name."""
        data = self.client_socket.recv(1024).decode()

        if "Server is full" in data:
            print(data) 
            self.client_socket.close()  
            exit(1) 

        self.client_name = f"Client0{data}"  # Assign a unique client name
        self.client_socket.send(self.client_name.encode())
        print("Client name: " + self.client_name)

    def print_help(self):
        """Print available commands for the user."""
        print("\nAvailable commands:")
        print("- status: Get server cache information")
        print("- list: Get list of available files")
        print("- get <filename>: Download a file")
        print("- exit: Close connection")
        print("- Any other message will be echoed back with ACK\n")

    def send_messages(self):
        """Send user input to the server until 'exit' is entered."""
        while True:
            try:
                if self.locked:
                    continue  # Prevent sending while downloading a file

                message = input(f"{self.client_name}> ")
                if not message:
                    continue
                
                self.client_socket.send(message.encode())
                
                if message.lower() == 'exit':
                    break  # Exit loop if user wants to disconnect
                    
                if message.lower().startswith('get '):
                    # Wait for the server to respond before allowing further input
                    continue
                    
            except Exception as e:
                print(f"Error sending message: {e}")
                break

    def receive_messages(self):
        """Continuously receive messages from the server."""
        while True:
            try:
                data = self.client_socket.recv(1024).decode()
                if not data:
                    break

                if data.startswith("Sending file: "):
                    self.locked = True  # Prevent input while file is being downloaded
                    self.receive_file(data[13:])
                else:
                   print(f"\rReceived: {data}\n{self.client_name}> ", end="", flush=True)
            except OSError:  # Handle socket closed errors
                break  
            except Exception as e:
                print(f"Error receiving message: {e}")
                break
            finally:
                self.locked = False
            
    def receive_file(self, filename: str):
        """Receive a file from the server and save it to the downloads folder."""
        try:
            file_path = os.path.join(self.downloads_folder, filename)
            self.client_socket.send(b"Ready")  # Signal readiness to receive
            print(f"Receiving file: {filename}", flush=True)
            
            with open(file_path, 'wb') as file:
                while True:
                    data = self.client_socket.recv(4096)
                    if data == b"END_OF_FILE" or not data:
                        break
                    self.client_socket.send(b"Ready")  # Acknowledge receipt of data
                    file.write(data)
                
            print(f"\nFile downloaded successfully.\n{self.client_name}> ", end="", flush=True)
            
        except Exception as e:
            print(f"Error receiving file: {e}")

if __name__ == '__main__':
    client = TCPClient()
    client.start_client()
