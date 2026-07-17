import socket
import threading
import json
import queue

class GameServer:
    def __init__(self, host='0.0.0.0', port=5555, target_players=2):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = []
        self.running = False
        self.message_queue = queue.Queue()
        self.next_id = 1
        self.target_players = target_players

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(4)
            self.running = True
            threading.Thread(target = self.accept_clients, daemon = True).start()
        except Exception as e:
            print(f"Server start error: {e}")
            self.running = False

    def stop(self):
        self.running = False
        try:
            self.server_socket.close()
        except (OSError, ConnectionResetError):
            pass
        for c in self.clients:
            try:
                c["connection"].close()
            except (OSError, ConnectionResetError):
                pass
        self.clients.clear()

    def accept_clients(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                client_id = self.next_id
                self.next_id += 1
                self.clients.append({"connection": conn, "id": client_id})
                existing = [0] + [c["id"] for c in self.clients if c["id"] != client_id]
                init_msg = json.dumps({"action": "init", "id": client_id, "players": existing, "target_players": self.target_players}) + '\n'
                conn.sendall(init_msg.encode('utf-8'))
                self.message_queue.put({"connection": conn, "data": {"action": "internal_player_joined", "client_id": client_id}})
                self.broadcast({"action": "player_joined", "id": client_id}, exclude = client_id)
                threading.Thread(target = self.handle_client, args = (conn, client_id), daemon = True).start()
            except (OSError, ConnectionResetError):
                break
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

    def handle_client(self, conn, client_id):
        buffer = ""
        while self.running:
            try:
                data = conn.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8')
                while '\n' in buffer:
                    msg, buffer = buffer.split('\n', 1)
                    if msg.strip():
                        parsed = json.loads(msg)
                        parsed["client_id"] = client_id
                        self.message_queue.put({"connection": conn, "data": parsed})
            except (OSError, ConnectionResetError):
                break
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

        self.message_queue.put({"connection": conn, "data": {"action": "internal_player_left", "client_id": client_id}})
        self.clients = [c for c in self.clients if c["id"] != client_id]
        self.broadcast({"action": "player_left", "id": client_id})
        try:
            conn.close()
        except (OSError, ConnectionResetError):
            pass

    def broadcast(self, data_dict, exclude=None):
        msg = (json.dumps(data_dict) + '\n').encode('utf-8')
        for c in self.clients[:]:
            if c["id"] == exclude:
                continue
            try:
                c["connection"].sendall(msg)
            except OSError:
                if c in self.clients:
                    self.clients.remove(c)

class GameClient:
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.message_queue = queue.Queue()

    def connect(self):
        try:
            self.client_socket.settimeout(2.0)
            self.client_socket.connect((self.host, self.port))
            self.client_socket.settimeout(None)
            self.connected = True
            threading.Thread(target = self.receive_data, daemon = True).start()
        except Exception as e:
            print(f"Не удалось подключиться: {e}")
            self.connected = False
            self.client_socket.close()
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def disconnect(self):
        self.connected = False
        try:
            self.client_socket.close()
        except (OSError, ConnectionResetError):
            pass

    def receive_data(self):
        buffer = ""
        while self.connected:
            try:
                data = self.client_socket.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8')
                while '\n' in buffer:
                    msg, buffer = buffer.split('\n', 1)
                    if msg.strip():
                        self.message_queue.put(json.loads(msg))
            except (OSError, ConnectionResetError):
                break
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
        self.connected = False
        try:
            self.client_socket.close()
        except (OSError, ConnectionResetError):
            pass

    def send_data(self, data_dict):
        if self.connected:
            try:
                msg = (json.dumps(data_dict) + '\n').encode('utf-8')
                self.client_socket.sendall(msg)
            except ConnectionResetError:
                self.connected = False