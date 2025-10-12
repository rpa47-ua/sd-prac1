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
    try:
        msg_length = conn.recv(HEADER).decode(FORMAT)
        if msg_length:
            msg_length = int(msg_length.strip())
            return conn.recv(msg_length).decode(FORMAT)
    except Exception:
        pass
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

        self.central_client = None
        self.engine_client = None

    def _connect_central(self):
        try:
            self.central_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.central_client.settimeout(5.0)
            self.central_client.connect(self.CENTRAL_ADDR)
            print(f"[MONITOR] Conectado a la CENTRAL {self.CENTRAL_ADDR}")

            auth_msg = json.dumps({'tipo': 'AUTENTICACION', 'cp_id': self.cp_id})
            self.central_client.send(auth_msg.encode(FORMAT))
            return True
        except ConnectionRefusedError:
            print("[ERROR] No se pudo conectar a la central (conexión rechazada)")
            return False
        except socket.timeout:
            print("[ERROR] Timeout conectando a la central")
            return False
        except Exception as e:
            print(f"[ERROR] Conectando con la central: {e}")
            return False

    def _connect_engine(self):
        try:
            self.engine_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.engine_client.settimeout(5.0)
            self.engine_client.connect(self.ENGINE_ADDR)
            print(f"[MONITOR] Conectado al Engine {self.ENGINE_ADDR}")
            return True
        except ConnectionRefusedError:
            print("[ERROR] No se pudo conectar al engine (conexión rechazada)")
            return False
        except socket.timeout:
            print("[ERROR] Timeout conectando al engine")
            return False
        except Exception as e:
            print(f"[ERROR] Conectando con el engine: {e}")
            return False
    
    def _notify_central(self, status):
        if not self.central_client:
            return
        
        try:
            msg = json.dumps({'tipo': 'ESTADO', 'cp_id': self.cp_id, 'estado': status})
            self.central_client.send(msg.encode(FORMAT))
            print(f"[NOTIFICADO] Estado '{status}' enviado a la central")
        except socket.error as e:
            print(f"[ERROR] No se pudo notificar a la central: {e}")
        except Exception as e:
            print(f"[ERROR] Notificando estado: {e}")

    def _check_engine_status(self):
        if not self.engine_client:
            return

        try:
            send("STATUS?", self.engine_client)
            init_state = recv(self.engine_client)
            
            if init_state:
                with self.lock:
                    self.last_status = init_state
                print(f"[MONITOR] Estado inicial: {init_state}")
                self._notify_central(init_state)
            else:
                print("[ERROR] No se pudo obtener estado inicial")
                self.running = False
                return
        except Exception as e:
            print(f"[ERROR] Obteniendo estado inicial: {e}")
            self.running = False
            return

        while self.running:
            try:
                send("STATUS?", self.engine_client)
                current_state = recv(self.engine_client)
                
                if not current_state:
                    print("[ERROR] Conexión perdida con el engine")
                    break

                with self.lock:
                    if current_state != self.last_status:
                        print(f"[CAMBIO DE ESTADO] {self.last_status} -> {current_state}")
                        self.last_status = current_state

                    self._notify_central(current_state)

                    if current_state == self.last_status:
                        print(f"[ESTADO ACTUAL] {current_state}")

                time.sleep(1)
                
            except socket.error as e:
                print(f"[ERROR] Comunicación con engine: {e}")
                break
            except Exception as e:
                if self.running:
                    print(f"[ERROR] Chequeando estado: {e}")
                break

    def _cleanup(self):
        print("\n[INFO] Cerrando conexiones...")
        self.running = False

        if self.engine_client:
            try:
                self.engine_client.shutdown(socket.SHUT_RDWR)
                self.engine_client.close()
                print("[INFO] Conexión con engine cerrada")
            except Exception:
                pass

        if self.central_client:
            try:
                # Enviar mensaje de desconexión explícita antes de cerrar
                goodbye_msg = json.dumps({'tipo': 'DESCONEXION', 'cp_id': self.cp_id})
                self.central_client.send(goodbye_msg.encode(FORMAT))
                time.sleep(0.1)  # Dar tiempo a que llegue el mensaje
                self.central_client.shutdown(socket.SHUT_RDWR)
                self.central_client.close()
                print("[INFO] Conexión con central cerrada")
            except Exception:
                pass

        print("[MONITOR] Aplicación finalizada")

    def start(self):
        print(f"=== Monitor del Punto de Carga: {self.cp_id} ===\n")

        if not self._connect_central():
            print("[ERROR] No se pudo establecer conexión con la central")
            self.running = False
            return

        if not self._connect_engine():
            print("[ERROR] No se pudo establecer conexión con el engine")
            self.running = False
            return

        print("\n[INFO] Monitoreando estado del punto de carga...")
        print("[INFO] Presiona Ctrl+C para salir\n")

        thread = threading.Thread(target=self._check_engine_status, daemon=True)
        thread.start()

        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[INFO] Interrupción por teclado")
        finally:
            self._cleanup()

def main():
    if len(sys.argv) < 4:
        print("Uso: python main.py [ip_engine:port_engine] [ip_central:port_central] <cp_id>") 
        print("Ejemplo: python main.py localhost:5050 localhost:3306 CP001")
        sys.exit(1)

    engine_ip, engine_port = sys.argv[1].split(':')
    central_ip, central_port = sys.argv[2].split(':')
    cp_id = sys.argv[3]

    monitor = EVChargingPointMonitor(engine_ip, engine_port, central_ip, central_port, cp_id)
    monitor.start()

if __name__ == "__main__":
    main()