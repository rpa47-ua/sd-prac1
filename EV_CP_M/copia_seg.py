import sys
import json
import time
import socket
import threading

FORMAT = 'utf-8'
HEADER = 64

def send(msg, conn):
    message = msg.encode(FORMAT)
    msg_length = len(message)
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
        self.manually_stopped = False
        
        self.central_client = None
        self.engine_client = None
        
        self.lock = threading.Lock()

    ### CENTRAL

    def _connect_central(self):
        """Conexión inicial a la CENTRAL"""
        while self.running and not self.central_client:
            try:
                self.central_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.central_client.settimeout(5)
                self.central_client.connect((self.central_ip, self.central_port))
                auth_msg = json.dumps({'tipo': 'AUTENTICACION', 'cp_id': self.cp_id})
                self.central_client.send(auth_msg.encode(FORMAT))
                print(f"[MONITOR] Conectado a CENTRAL {self.central_ip}:{self.central_port}")
                threading.Thread(target=self._listen_central, daemon=True).start()

                if self.last_status:
                    msg = json.dumps({'tipo': self.last_status, 'cp_id': self.cp_id})
                    self.central_client.send(msg.encode(FORMAT))
                    print(f"[CENTRAL] Estado actual '{self.last_status}' enviado tras conexión inicial")

                return True
            except Exception:
                print(f"[ERROR] No se pudo conectar a CENTRAL, reintentando en 3 segundos...")
                try:
                    if self.central_client:
                        self.central_client.close()
                except: pass
                self.central_client = None
                time.sleep(3)
        return False

    def _central_reconnect_loop(self):
        """Hilo que intenta reconectar a CENTRAL constantemente"""
        while self.running:
            if not self.central_client:
                try:
                    self.central_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.central_client.settimeout(5)
                    self.central_client.connect((self.central_ip, self.central_port))
                    auth_msg = json.dumps({'tipo': 'AUTENTICACION', 'cp_id': self.cp_id})
                    self.central_client.send(auth_msg.encode(FORMAT))
                    print(f"[MONITOR] Reconectado a CENTRAL {self.central_ip}:{self.central_port}")
                    threading.Thread(target=self._listen_central, daemon=True).start()

                    if self.last_status:
                        msg = json.dumps({'tipo': self.last_status, 'cp_id': self.cp_id})
                        self.central_client.send(msg.encode(FORMAT))
                        print(f"[CENTRAL] Estado actual '{self.last_status}' enviado tras reconexión")

                except Exception:
                    print(f"[ERROR] No se pudo reconectar a CENTRAL, reintentando en 3 segundos...")
                    try:
                        if self.central_client:
                            self.central_client.close()
                    except: pass
                    self.central_client = None
                    time.sleep(3)
            else:
                time.sleep(1)

    def _notify_central(self, state):
        if self.central_client:
            try:
                msg = json.dumps({'tipo': state, 'cp_id': self.cp_id})
                self.central_client.send(msg.encode(FORMAT))
                print(f"[CENTRAL] Estado '{state}' enviado")
            except Exception as e:
                print(f"[ERROR] Al notificar a CENTRAL: {e}")
                try:
                    self.central_client.close()
                except: pass
                self.central_client = None

    def _listen_central(self):
        print("[MONITOR] Escuchando comandos de la CENTRAL...")
        while self.running and self.central_client:
            try:
                self.central_client.settimeout(2.0)
                data = self.central_client.recv(4096)
                if not data:
                    print("[MONITOR] CENTRAL cerró la conexión")
                    break
                try:
                    mensaje = json.loads(data.decode(FORMAT))
                    tipo = mensaje.get('tipo')
                    with self.lock:
                        if tipo == 'PARAR':
                            self.manually_stopped = True
                            print("[CENTRAL] Comando: PARAR recibido, CP detenido manualmente")
                        elif tipo == 'REANUDAR':
                            self.manually_stopped = False
                            print("[CENTRAL] Comando: REANUDAR recibido, CP activo")
                        self.last_status = None
                except json.JSONDecodeError:
                    pass
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[ERROR] Escuchando comandos de CENTRAL: {e}")
                break
        print("[MONITOR] Dejó de escuchar comandos de la CENTRAL")
        if self.central_client:
            try:
                self.central_client.close()
            except:
                pass
            self.central_client = None
            print("[MONITOR] Conexión con CENTRAL cerrada")

    ### ENGINE

    def _connect_engine(self):
        while self.running and not self.engine_client:
            try:
                self.engine_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.engine_client.settimeout(5)
                self.engine_client.connect((self.engine_ip, self.engine_port))
                print(f"[MONITOR] Conectado a ENGINE {self.engine_ip}:{self.engine_port}")
                return True
            except Exception as e:
                print(f"[ERROR] No se pudo conectar a ENGINE: {e}")
                time.sleep(2)
        return False

    def _check_engine_status(self):
        print("[MONITOR] Comenzando monitoreo del Engine...")
        while self.running:
            if not self.engine_client:
                if not self._connect_engine():
                    time.sleep(1)
                    continue

            try:
                send("STATUS?", self.engine_client)
                current_state = recv(self.engine_client)

                with self.lock:
                    if not current_state:
                        estado = "AVERIA" if not self.manually_stopped else "PARADO"
                        if self.engine_client:
                            try: self.engine_client.close()
                            except: pass
                            self.engine_client = None
                    else:
                        estado = "PARADO" if self.manually_stopped else current_state

                    if self.last_status != estado:
                        prev_status = self.last_status or "NINGUNO"
                        print(f"[MONITOR] Cambio de estado: {prev_status} -> {estado}")
                        self.last_status = estado
                        self._notify_central(estado)
                    else:
                        print(f"[MONITOR] Estado actual: {estado}")

                time.sleep(1)

            except (socket.error, ConnectionResetError):
                print("[ERROR] Comunicación con Engine perdida, reconectando...")
                if self.engine_client:
                    try: self.engine_client.close()
                    except: pass
                self.engine_client = None
                with self.lock:
                    estado = "AVERIA" if not self.manually_stopped else "PARADO"
                    if self.last_status != estado:
                        self.last_status = estado
                        self._notify_central(estado)
                time.sleep(2)
            except Exception as e:
                print(f"[ERROR] Chequeo Engine: {e}")

    ### MONITOR

    def _cleanup(self):
        print("\n[MONITOR] Cerrando conexiones...")
        self.running = False
        if self.engine_client:
            try: self.engine_client.close()
            except: pass
        if self.central_client:
            try: self.central_client.close()
            except: pass
        print("[MONITOR] Aplicación finalizada correctamente")

    def start(self):
        print(f"=== Monitor del Punto de Carga: {self.cp_id} ===\n")
        
        self._connect_central()
        self._connect_engine()

        threading.Thread(target=self._central_reconnect_loop, daemon=True).start()
        threading.Thread(target=self._check_engine_status, daemon=True).start()

        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[MONITOR] Interrupción por teclado")
        finally:
            self._cleanup()

def main():
    if len(sys.argv) < 4:
        print("Uso: python main.py [ip_engine:port_engine] [ip_central:port_central] <cp_id>")
        print("Ejemplo: python main.py localhost:5050 localhost:5000 CP001")
        sys.exit(1)

    engine_ip, engine_port = sys.argv[1].split(':')
    central_ip, central_port = sys.argv[2].split(':')
    cp_id = sys.argv[3]

    monitor = EVChargingPointMonitor(engine_ip, engine_port, central_ip, central_port, cp_id)
    monitor.start()

if __name__ == "__main__":
    main()