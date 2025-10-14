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

    def _connect_central(self):
        while self.running:
            try:
                self.central_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.central_client.settimeout(5)
                self.central_client.connect((self.central_ip, self.central_port))

                auth_msg = json.dumps({'tipo': 'AUTENTICACION', 'cp_id': self.cp_id})
                self.central_client.send(auth_msg.encode(FORMAT))

                print(f"[MONITOR] Conectado a CENTRAL {self.central_ip}:{self.central_port}")

                threading.Thread(target=self._listen_central_commands, daemon=True).start()

                with self.lock:
                    self.last_status = None

                return True
            except Exception as e:
                print(f"[ERROR] No se pudo conectar a CENTRAL: {e}")
                time.sleep(2)
        return False

    def _connect_engine(self):
        while self.running:
            try:
                self.engine_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.engine_client.settimeout(5.0)
                self.engine_client.connect((self.engine_ip, self.engine_port))
                
                print(f"[MONITOR] Conectado a ENGINE {self.engine_ip}:{self.engine_port}")
                return True
            except Exception as e:
                print(f"[ERROR] No se pudo conectar a ENGINE: {e}")
                time.sleep(2)
        return False
    
    def _notify_central(self, state):
        if not self.central_client:
            print("[ERROR] Conexión con central no disponible")
            return
        try:
            msg = json.dumps({'tipo': state, 'cp_id': self.cp_id})
            self.central_client.send(msg.encode(FORMAT))
            print(f"[NOTIFICADO] Estado '{state}' enviado a CENTRAL")
        except Exception as e:
            print(f"[ERROR] Al notificar a CENTRAL: {e}")
            try:
                self.central_client.close()
            except:
                pass
            self.central_client = None

    def _listen_central_commands(self):
        """Escucha comandos entrantes de la Central (PARAR/REANUDAR)"""
        print("[MONITOR] Escuchando comandos de la Central...")
        while self.running and self.central_client:
            try:
                self.central_client.settimeout(2.0)
                data = self.central_client.recv(4096)

                if not data:
                    print("[MONITOR] Central cerró la conexión")
                    break

                try:
                    mensaje = json.loads(data.decode(FORMAT))
                    tipo = mensaje.get('tipo')

                    if tipo == 'PARAR':
                        with self.lock:
                            self.manually_stopped = True
                            self.last_status = None
                        print("[COMANDO] CP parado manualmente desde Central")

                    elif tipo == 'REANUDAR':
                        with self.lock:
                            self.manually_stopped = False
                            self.last_status = None
                        print("[COMANDO] CP reanudado desde Central")

                except json.JSONDecodeError:
                    pass

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[ERROR] Escuchando comandos de Central: {e}")
                break

        print("[MONITOR] Dejó de escuchar comandos de la Central")
        if self.central_client:
            try:
                self.central_client.close()
            except:
                pass
            self.central_client = None
            print("[MONITOR] Conexión con Central cerrada, se reintentará conexión...")

    def _check_engine_status(self):
        print("[MONITOR] Iniciando chequeo del estado del Engine...")

        while self.running:
            if not self.central_client:
                print("[RECONEXIÓN] Intentando reconectar a la Central...")
                if not self._connect_central():
                    time.sleep(2)
                    continue
                else:
                    print("[OK] Reconectado a Central, enviando estado actual...")

            if not self.engine_client:
                print("[INFO] Intentando reconectar al Engine...")

                if not self.manually_stopped:
                    with self.lock:
                        estado_a_enviar = "AVERIA"
                        if self.last_status != estado_a_enviar:
                            print("[ENGINE CAIDO] Reportando AVERIA a Central")
                            self.last_status = estado_a_enviar
                            self._notify_central(estado_a_enviar)

                if not self._connect_engine():
                    time.sleep(2)
                    continue
                else:
                    print("[OK] Reconectado a Engine")
                    with self.lock:
                        self.last_status = None

            try:
                send("STATUS?", self.engine_client)
                current_state = recv(self.engine_client)

                if not current_state:
                    print("[ERROR] No se recibió respuesta del Engine - Engine caído")
                    try:
                        self.engine_client.close()
                    except:
                        pass
                    self.engine_client = None

                    if not self.manually_stopped:
                        with self.lock:
                            estado_a_enviar = "AVERIA"
                            if self.last_status != estado_a_enviar:
                                print("[ENGINE CAIDO] Reportando AVERIA a Central")
                                self.last_status = estado_a_enviar
                                self._notify_central(estado_a_enviar)

                    time.sleep(2)
                    continue

                with self.lock:
                    state = "PARADO" if self.manually_stopped else current_state

                    if self.last_status != state:
                        print(f"[CAMBIO DE ESTADO] {self.last_status} -> {state}" if self.last_status else f"[ESTADO INICIAL] {state}")
                        self.last_status = state
                        self._notify_central(state)
                    else:
                        print(f"[ESTADO ACTUAL] {state}")

                time.sleep(1)

            except (socket.error, ConnectionResetError):
                print("[ERROR] Comunicación con Engine perdida. Intentando reconectar...")
                if self.engine_client:
                    try:
                        self.engine_client.close()
                    except:
                        pass
                self.engine_client = None

                if not self.manually_stopped:
                    with self.lock:
                        estado_a_enviar = "AVERIA"
                        if self.last_status != estado_a_enviar:
                            print("[ENGINE CAIDO] Reportando AVERIA a Central")
                            self.last_status = estado_a_enviar
                            self._notify_central(estado_a_enviar)

                time.sleep(2)
            except Exception as e:
                print(f"[ERROR] check estado {e}")

    def _cleanup(self):
        print("\n[INFO] Cerrando conexiones...")
        self.running = False

        if self.engine_client:
            try:
                self.engine_client.close()
            except:
                pass
            
        if self.central_client:
            try:
                self.central_client.close()
            except:
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
        print("Ejemplo: python main.py localhost:5050 localhost:5000 CP001")
        sys.exit(1)

    engine_ip, engine_port = sys.argv[1].split(':')
    central_ip, central_port = sys.argv[2].split(':')
    cp_id = sys.argv[3]

    monitor = EVChargingPointMonitor(engine_ip, engine_port, central_ip, central_port, cp_id)
    monitor.start()


if __name__ == "__main__":
    main()