import sys
import json
import time
import socket
import threading
import random
from kafka import KafkaProducer, KafkaConsumer

FORMAT = 'utf-8'
HEADER = 64
FIN = 'FIN'

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

class EVChargingPointEngine:
    def __init__(self, broker, cp_id, monitor_ip, monitor_port):
        self.broker = broker
        self.cp_id = cp_id
        self.monitor_ip = monitor_ip
        self.monitor_port = int(monitor_port)
        self.breakdown_status = False
        self.charging = False
        self.running = True
        self.kWH = abs(1 - random.random()) # 0.0 ≤ x < 1.0
        self.price = abs(1 - random.random())
        self.lock = threading.Lock()

        self.producer = KafkaProducer(
            bootstrap_servers = self.broker,
            value_serializer = lambda v: json.dumps(v).encode('utf-8')
        )

        self.consumer = KafkaConsumer(
            bootstrap_servers = self.broker,
            value_deserializer = lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=True
        )

        self.consumer.subscribe(['respuestas_cp'])

        self.monitor_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.monitor_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.monitor_server.bind((self.monitor_ip, self.monitor_port))
        self.monitor_server.listen(5)
        self.monitor_server.settimeout(1.0)

        self.thread_kafka  = threading.Thread(target=self._listen_kafka, daemon=True)
        self.thread_monitor  = threading.Thread(target=self._listen_monitor, daemon=True)
        self.thread_kafka.start()
        self.thread_monitor.start()

    def _handle_monitor(self, conn, addr):
        print(f"[MONITOR CONECTADO] {addr}")
        try:
            while self.running:
                msg = recv(conn)

                if not msg:
                    break
                if msg == "STATUS?":
                    status = "AVERIA" if self.breakdown_status else "OK"
                    send(status, conn)
        except Exception as e :
            print(f"[ERROR] monitor {addr}: {e}")
        finally:
            conn.close()
            print(f"[MONITOR DESCONECTADO] {addr}")

    def _listen_monitor(self):
        while self.running:
            try:
                conn, addr = self.monitor_server.accept()
                threading.Thread(target=self._handle_monitor, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[ERROR] {e}")

    def _send_charging_request(self, driver_id):
        with self.lock:
            if self.charging:
                print("[ERROR] CP ya está suministrando")
                return 
        
        print(f"[SOLICITUD] de conductor: {driver_id}")

        request = {'conductor_id': driver_id, 'cp_id': self.cp_id, 'origen': 'CP'}
        self.producer.send('solicitudes_suministro', request)
        self.producer.flush()

        if self._wait_authorization():
            self._supply(driver_id)

    def _listen_kafka(self):
        try:
            for msg in self.consumer:
                if not self.running:
                    break

                kmsg = msg.value

                if msg.topic == 'respuestas_cp' and kmsg.get('cp_id') == self.cp_id:
                    if kmsg.get('autorizado', False):
                        print(f"[AUTORIZADO] {kmsg.get('mensaje')}")
                        with self.lock:
                            self.charging = True
                    else:
                        print(f"[DENEGADO] {kmsg.get('mensaje')}")
        except Exception:
            print("[ERROR]")

    def _wait_authorization(self, timeout=10): # Repasar
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.lock:
                if self.charging:
                    return True
            time.sleep(0.5)
        
        print("[TIMEOUT] No se recibió autorización")
        return False

    def _supply(self, driver_id):
        acc_price = 0
        consumed_kWH = 0
        while True:
            with self.lock:
                if not self.charging:
                    break
                if self.breakdown_status:
                    print("[AVERIA] Suministro interrumpido por avería")
                    self._notify_breakdown(driver_id)
                    self.charging = False
                    break
            
            consumed_kWH += self.kWH
            acc_price += consumed_kWH * self.price * 10
            telemetry = {'cp_id': self.cp_id, 'conductor_id': driver_id, 'consumo_actual': consumed_kWH, 'importe_actual': acc_price}
            self.producer.send('telemetria_cp', telemetry)
            time.sleep(1)

        with self.lock:
            if not self.breakdown_status:
                self._send_ticket(driver_id, consumed_kWH, acc_price)
            self.charging = False

    def _send_ticket(self, driver_id, consumed_kWH, total_price): #Arreglar suministro_id
        ticket = {'conductor_id': driver_id, 'cp_id': self.cp_id, 'suministro_id': self.cp_id, 'consumo_kwh': consumed_kWH, 'importe_total': total_price}
        self.producer.send('tickets', ticket)
        self.producer.flush()
        print(f"[TICKET ENVIADO]")

    def _notify_breakdown(self, driver_id):
        notification = {'conductor_id': driver_id, 'cp_id': self.cp_id, 'tipo': 'AVERIA_DURANTE_SUMINISTRO', 'mensaje': f'Suministro interrumpido por avería en {self.cp_id}'}
        self.producer.send('notificaciones', notification)
        self.producer.flush()

    def start(self):
        cp_init = {'cp_id': self.cp_id}
        self.producer.send('iniciar_cp', cp_init)
        self.producer.flush()

        print(f"=== Punto de Carga: {self.cp_id} ===")
        print("Comandos disponibles:")
        print("  S <DRIVER_ID>  - Solicitar suministro para conductor")
        print("  F              - Finalizar suministro actual")
        print("  A              - Simular avería")
        print("  R              - Reparar avería")
        print("  salir          - Salir de la aplicación\n")

        while True:
            try:
                u_input = input("> ").strip()

                if not u_input: 
                    continue
                    
                if u_input.lower() == 'salir':
                    break
                elif u_input.upper() == 'A':
                    with self.lock:
                        self.breakdown_status = True
                    print("[AVERIA] Estado cambiado a AVERIA")
                    
                elif u_input.upper() == 'R':
                    with self.lock:
                        self.breakdown_status = False
                    print("[REPARADO] Estado cambiado a OK")
                    
                elif u_input.upper() == 'F':
                    with self.lock:
                        if self.charging:
                            self.charging = False
                            print("[FINALIZANDO] Suministro detenido manualmente")
                        else:
                            print("[ERROR] No hay ningún suministro en curso")
                            
                elif u_input.upper().startswith('S '):
                    parts = u_input.split(maxsplit=1)
                    if len(parts) > 1:
                        driver_id = parts[1].strip()
                        self._send_charging_request(driver_id)
                    else:
                        print("[ERROR] Formato: S <DRIVER_ID>")
                else:
                    print("[ERROR] Comando no reconocido")
                    
            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[ERROR] {e}")


    def end(self):
        print("\n[INFO] Cerrando aplicación...")
        self.running = False
        
        if self.thread_kafka.is_alive():
            self.thread_kafka.join(timeout=2)
        if self.thread_monitor.is_alive():
            self.thread_monitor.join(timeout=2)
        
        self.consumer.close()
        self.producer.close()
        self.monitor_server.close()

def main():
    if len(sys.argv) < 4:
        print("Uso: python engine.py [ip_broker:port_broker] [ip_monitor:port_monitor] <cp_id>")
        print("python main.py localhost:9092 localhost:5050 CP001")
        sys.exit(1)

    broker = sys.argv[1]
    monitor_ip, monitor_port = sys.argv[2].split(':')
    cp_id = sys.argv[3]
    engine = EVChargingPointEngine(broker, cp_id, monitor_ip, monitor_port)

    try:
        engine.start()
    except KeyboardInterrupt:
        print("Aplicacion interrumpida por el usuario")
    finally:
        engine.end()

if __name__ == "__main__":
    main()