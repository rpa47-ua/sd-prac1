import sys
import json
import time
import socket
import threading

FORMAT = 'utf-8'
HEADER = 64

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
        self.parado_manualmente = False  # Estado de parada manual desde Central
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

                # Iniciar hilo para escuchar comandos de la Central
                threading.Thread(target=self._listen_central_commands, daemon=True).start()

                # Resetear last_status para forzar envío de estado en siguiente ciclo
                # Esto asegura que la Central reciba el estado actual tras reconexión
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
                # Configurar timeout para no bloquear indefinidamente
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
                            self.parado_manualmente = True
                            self.last_status = None  # Forzar envío de estado en siguiente ciclo
                        print("[COMANDO] CP parado manualmente desde Central")

                    elif tipo == 'REANUDAR':
                        with self.lock:
                            self.parado_manualmente = False
                            self.last_status = None  # Forzar envío de estado en siguiente ciclo
                        print("[COMANDO] CP reanudado desde Central")

                except json.JSONDecodeError:
                    pass  # Ignorar mensajes mal formados

            except socket.timeout:
                continue  # Timeout normal, seguir esperando
            except Exception as e:
                if self.running:
                    print(f"[ERROR] Escuchando comandos de Central: {e}")
                break

        # Al salir del bucle, cerrar conexión y marcar como desconectado
        print("[MONITOR] Dejó de escuchar comandos de la Central")
        if self.central_client:
            try:
                self.central_client.close()
            except:
                pass
            self.central_client = None
            print("[MONITOR] Conexión con Central cerrada, se reintentará conexión...")

    def _check_engine_status(self):
        while self.running:
            # Verificar conexión a Central primero
            if not self.central_client:
                print("[RECONEXIÓN] Intentando reconectar a la Central...")
                if not self._connect_central():
                    time.sleep(2)
                    continue
                else:
                    print("[OK] Reconectado a Central, enviando estado actual...")

            # Si no hay conexión al Engine, reportar AVERIA a la Central
            if not self.engine_client:
                print("[INFO] Intentando reconectar al Engine...")

                # Mientras no haya Engine, reportar AVERIA
                if not self.parado_manualmente:
                    with self.lock:
                        estado_a_enviar = "AVERIA"
                        if self.last_status != estado_a_enviar:
                            print(f"[ENGINE CAIDO] Reportando AVERIA a Central")
                            self.last_status = estado_a_enviar
                            self._notify_central(estado_a_enviar)

                if not self._connect_engine():
                    time.sleep(2)
                    continue
                else:
                    # Se reconectó al Engine, resetear last_status para forzar actualización
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

                    # Reportar AVERIA cuando el Engine no responde
                    if not self.parado_manualmente:
                        with self.lock:
                            estado_a_enviar = "AVERIA"
                            if self.last_status != estado_a_enviar:
                                print(f"[ENGINE CAIDO] Reportando AVERIA a Central")
                                self.last_status = estado_a_enviar
                                self._notify_central(estado_a_enviar)

                    time.sleep(2)
                    continue

                with self.lock:
                    # Si está parado manualmente, enviar PARADO en vez del estado real
                    estado_a_enviar = "PARADO" if self.parado_manualmente else current_state

                    if self.last_status != estado_a_enviar:
                        print(f"[CAMBIO DE ESTADO] {self.last_status} -> {estado_a_enviar}" if self.last_status else f"[ESTADO INICIAL] {estado_a_enviar}")
                        self.last_status = estado_a_enviar
                        self._notify_central(estado_a_enviar)
                    else:
                        print(f"[ESTADO ACTUAL] {estado_a_enviar}")

                time.sleep(1)

            except (socket.error, ConnectionResetError):
                print("[ERROR] Comunicación con Engine perdida. Intentando reconectar...")
                if self.engine_client:
                    try:
                        self.engine_client.close()
                    except:
                        pass
                self.engine_client = None

                # Reportar AVERIA cuando se pierde conexión con Engine
                if not self.parado_manualmente:
                    with self.lock:
                        estado_a_enviar = "AVERIA"
                        if self.last_status != estado_a_enviar:
                            print(f"[ENGINE CAIDO] Reportando AVERIA a Central")
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
        print("Ejemplo: python main.py localhost:5050 localhost:3306 CP001")
        sys.exit(1)

    engine_ip, engine_port = sys.argv[1].split(':')
    central_ip, central_port = sys.argv[2].split(':')
    cp_id = sys.argv[3]

    monitor = EVChargingPointMonitor(engine_ip, engine_port, central_ip, central_port, cp_id)
    monitor.start()

if __name__ == "__main__":
    main()