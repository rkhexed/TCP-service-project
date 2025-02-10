import socket
import os
import threading

class TCPClient:
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = 'localhost'
        self.port = 12345
        self.client_name = None
        self.downloads_folder = "client_downloads"
        self.locked = False
        
        # Create downloads folder if it doesn't exist
        if not os.path.exists(self.downloads_folder):
            os.makedirs(self.downloads_folder)

    def start_client(self):
        try:
            self.client_socket.connect((self.host, self.port))

            #get client name
            self.send_client_name()
            
            # Start receive thread
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()

            
        
            # Print available commands
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
        data = self.client_socket.recv(1024).decode()

        if "Server is full" in data:
            print(data) 
            self.client_socket.close()  
            exit(1) 

        self.client_name = f"Client0{data}"
        #communicate back the name
        self.client_socket.send(self.client_name.encode())
        print("Client name: " + self.client_name)

    def print_help(self):
        print("\nAvailable commands:")
        print("- status: Get server cache information")
        print("- list: Get list of available files")
        print("- get <filename>: Download a file")
        print("- exit: Close connection")
        print("- Any other message will be echoed back with ACK\n")

    def send_messages(self):
        while True:
            try:
                if self.locked:
                    #print(f"{self.client_name} is currently receiving a file. Skipping message input.") # Debugging line
                    continue


                message = input(f"{self.client_name}> ")
                if not message:
                    continue
                
                self.client_socket.send(message.encode())
                
                if message.lower() == 'exit':
                    break
                    
                if message.lower().startswith('get '):
                    # Wait for server response before continuing
                    continue
                    
            except Exception as e:
                print(f"Error sending message: {e}")
                break

    def receive_messages(self):
        while True:
            try:
                data = self.client_socket.recv(1024).decode()
                if not data:
                    break

                if data.startswith("Sending file: "):
                    self.locked = True
                    self.receive_file(data[13:])
                else:
                   print(f"\rReceived: {data}\n{self.client_name}> ", end = "",  flush = True)

            except OSError:  # socket closed error
                break  #exit
                    
            except Exception as e:
                print(f"Error receiving message: {e}")
                break
            finally:
                self.locked = False
            
    def receive_file(self, filename: str):
        try:
            file_path = os.path.join(self.downloads_folder, filename)
            self.client_socket.send(b"Ready")  # Signal ready to receive
            print(f"recieving file: {filename}", flush = True)
            
            with open(file_path, 'wb') as file:
                #print("file opened")
                while True:
                    #print("t" , end = " ")
                    data = self.client_socket.recv(4096)

                    if data == b"END_OF_FILE" or not data:
                        #print("EOF REACHED")
                        break
                    self.client_socket.send(b"Ready")  # SAY PAYLOAD RECIEVED, GO NEXT
                    #print(f"Received {len(data)} bytes...")
                    file.write(data)
                
            
            print(f"\nFile downloaded successfully.\n{self.client_name}> ", end = "",  flush = True)
            
        except Exception as e:
            print(f"Error receiving file: {e}")

if __name__ == '__main__':
    client = TCPClient()
    client.start_client()