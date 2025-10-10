import sys
import json
import time
import socket
import threading
import json
import random

FORMAT = 'utf-8'
HEADER = 64
FIN = 'FIN'

def send(msg, conn):
    message = msg.encode(FORMAT)
    msg_length= len(message)
    send_length = str(msg_length).encode(FORMAT)
    send_length += b' ' * (HEADER - len(send_length))
    conn.send(send_length)
    conn.send(message)

def recv(conn):
    msg_length = conn.recv(HEADER).decode(FORMAT)
    if msg_length:
        msg_length = int(msg_length.strip())
        return conn.recv(msg_length).decode(FORMAT)
    return None

class EVChargingPointMonitor:
    def __init__(self, engine_ip, engine_port, central_ip, central_port, cp_id):
        self.engine_ip = engine_ip
        self.engine_port = int(engine_port)
        self.central_ip = central_ip
        self.central_port = int(central_port)
        self.cp_id = cp_id
        self.last_status = None
        self.running = True
        self.lock = threading.Lock()

        self.ENGINE_ADDR = (self.engine_ip, self.engine_port)
        self.CENTRAL_ADDR = (self.central_ip, self.central_port)

        self.central_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.engine_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def _connect_central(self):
        try:
            self.central_client.connect(self.CENTRAL_ADDR)
            print(f"[MONITOR] Conectado a la CENTRAL {self.CENTRAL_ADDR}")

            auth_msg = json.dumps({'tipo': 'AUTENTICACION', 'cp_id': self.cp_id})
            self.central_client.send(auth_msg.encode(FORMAT))
        except ConnectionRefusedError:
            print("[ERROR] No se pudo conectar a la central.")
            self.running = False
        except Exception as e:
            print(f"[ERROR] Error conectando con la central: {e}")
            self.running = False

    def _connect_engine(self):
        try:
            self.engine_client.connect(self.ENGINE_ADDR)
            print(f"[MONITOR] Conectado al Engine {self.ENGINE_ADDR}")
        except ConnectionRefusedError:
            print("[ERROR] No se pudo conectar al engine.")
            self.running = False
        except Exception as e:
            print(f"[ERROR] Error conectando con la central: {e}")
            self.running = False
    
    def _notify_central(self, status):
        try:
            msg = json.dumps({'tipo': 'ESTADO', 'cp_id': self.cp_id, 'estado': status})
            self.central_client.send(msg.encode(FORMAT))
        except Exception as e:
            print(f"No se pudo notificar a la central {e}")

    def _check_engine_status(self):
        send("STATUS?", self.engine_client)
        init_state = recv(self.engine_client)
        self.last_status = init_state
        print(f"[MONITOR] Estado inicial: {init_state}")

        while self.running:
            send("STATUS?", self.engine_client)
            current_state = recv(self.engine_client)
            if current_state != self.last_status:
                print(f"[MONITOR] Cambio de estado a: {current_state}")
                self.last_status = current_state

            print(f"[MONITOR] Estado actual: {current_state}")
            time.sleep(1)

    def start(self):
        self._connect_central()
        self._connect_engine()

        if not self.running:
            print("[ERROR] Error en la conexion")

        thread = threading.Thread(target=self._check_engine_status, daemon=True)
        thread.start()

        try: #Hilo principal a la espera o interrupcion por teclado
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.running = False
        finally:
            self.engine_client.close()
            self.central_client.close()
            print("[MONITOR] Conexiones cerradas.")

def main():
    if len(sys.argv) < 4:
        print("Uso: python main.py [ip_engine:port_engine] [ip_central:port_central] <cp_id>") 
        print("Ejemplo: python main.py 0.0.0.0:5050  0.0.0.1:5051 3")
        sys.exit(1)

    engine_ip, engine_port = sys.argv[1].split(':')
    central_ip, central_port = sys.argv[2].split(':')
    cp_id = sys.argv[3]

    monitor = EVChargingPointMonitor(engine_ip, engine_port, central_ip, central_port, cp_id)
    monitor.start()

if __name__ == "__main__":
    main()