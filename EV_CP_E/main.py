import sys
import json
import time
import socket
import threading
import random
from kafka import KafkaProducer, KafkaConsumer

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

class EVChargingPointEngine:
    def __init__(self, broker, cp_id, monitor_ip, monitor_port):
        self.broker = broker
        self.cp_id = cp_id
        self.monitor_ip = monitor_ip
        self.monitor_port = int(monitor_port)

        self.breakdown_status = False
        self.charging = False
        self.running = True
        self.current_driver = None
        self.current_supply_id = None

        self.kWH = abs(1 - random.random())
        self.price = abs(1 - random.random())

        self.lock = threading.Lock()

        self.producer = None
        self.consumer = None
        self._init_kafka()

        self._init_monitor()

    def _init_kafka(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.broker,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )

            self.consumer = KafkaConsumer(
                bootstrap_servers=self.broker,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True
            )

            self.consumer.subscribe(['respuestas_cp', 'respuestas_conductor'])
            print(f"[KAFKA] Conectado al broker {self.broker}")
        except Exception as e:
            print(f"[ERROR] Fallo conectando a Kafka: {e}")
            self.producer = None
            self.consumer = None

    def _reconnect_kafka(self):
        while self.running:
            print("[INFO] Reintentando conexión a Kafka")
            try:
                self._init_kafka()
                if self.producer and self.consumer:
                    print("[OK] Reconexión Kafa completada")
                    return
            except:
                print(f"[ERROR] Reconexion Kafka fallida")
            time.sleep(5)

    def _init_monitor(self):
        try:
            self.monitor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.monitor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.monitor.bind((self.monitor_ip, self.monitor_port))
            self.monitor.listen(5)
            self.monitor.settimeout(1)
            print(f"[MONITOR] Monitor activo en {self.monitor_ip}:{self.monitor_port}")
        except Exception as e:
            print(f"[ERROR] Fallo iniciando servidor monitor: {e}")
            self.monitor = None

    def _handle_monitor(self, conn, addr):
        print(f"[MONITOR CONECTADO] {addr}")
        try:
            while self.running:
                msg = recv(conn)
                if not msg:
                    break
                if msg == "STATUS?":
                    with self.lock:
                        status = "AVERIA" if self.breakdown_status else "OK"
                    try:
                        send(status, conn)
                    except Exception as e:
                        print(f"[ERROR] Enviar estado al monitor: {e}")
        except Exception as e :
            print(f"[ERROR] monitor {addr}: {e}")
        finally:
            try:
                conn.close()
            except:
                pass
            print(f"[MONITOR DESCONECTADO] {addr}")

    def _listen_monitor(self):
        while self.running:
            if not self.monitor:
                print("[ERROR] Monitor no disponible, intentando conexión")
                self._init_monitor()
                time.sleep(2)
                continue

            try: 
                conn, addr = self.monitor_server.accept()
                threading.Thread(target=self._handle_monitor, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[ERROR] {e}")
                    time.sleep(1)

    def _listen_kafka(self):
        while self.running:
            if not self.consumer:
                self._reconnect_kafka()
                time.sleep(2)
                continue
            
            try:
                records = self.consumer.poll(timeout_ms=1000)
                if not self.running:
                    break

                for tp, msgs in records.items():
                    for msg in msgs:
                        kmsg = msg.value
                        if msg.topic in ['respuestas_cp', 'respuestas_conductor'] and kmsg.get('cp_id') == self.cp_id:
                            self. _handle_authorization_response(kmsg)

            except Exception as e:
                print(f"[ERROR] Error en Kafka {e}")
                self._reconnect_kafka()
                time.sleep(2)

    def _handle_authorization_response(self, kmsg):
        if kmsg.get('autorizado', False):
            print(f"[AUTORIZADO] {kmsg.get('mensaje', 'Suministro autorizado')}")
            with self.lock:
                if not self.charging:
                    self.charging = True
                    self.current_driver = kmsg.get('conductor_id')
                    self.current_supply_id = kmsg.get('suministro_id')
                    threading.Thread(target=self._supply, daemon=True).start()
        else:
            print(f"[DENEGADO] {kmsg.get('mensaje', 'Suministro denegado')}")

    def _notify_breakdown(self, driver_id): # Esto no se si lo  deberia de hacer el propio cp o lo tiene que hacer la central al recibir el cambio de estado del monitor
        try:
            msg = {'tipo': 'AVERIA_DURANTE_SUMINISTRO', 'conductor_id': driver_id, 'cp_id': self.cp_id, 'mensaje': 'Suministro interrumpido por avería'}
            self.producer.send('notificaciones', msg) # Mirar si es este el topic donde se hay que mandar? (en caso  de que se tenga que hacer en el cp)
            self.producer.flush()
            print("[AVERIA] Averia comunicadad a central/conductor")
        except Exception as e:
            print(f"[ERROR] No se pudo notificar la averia: {e}")
            self._reconnect_kafka()

    def _supply(self):
        with self.lock:
            driver_id = self.current_driver
            supply_id = self.current_supply_id

        print(f"[SUMINISTRO INICIADO]")
        print(f"  Conductor: {driver_id}")
        print(f"  ID: {supply_id}")
        print(f"  Precio: {self.price} EUR/kWh")
        
        consumed_kwh = 0
        total_price = 0
        pending_telemetry = []

        while True:
            with self.lock:
                if not self.charging or not self.running:
                    break
                if self.breakdown_status:
                    print("[AVERIA] Suministro interrumpido")
                    self._notify_breakdown(driver_id)
                    self.charging = False
                    break

            consumed_kwh += self.kWH
            total_price = consumed_kwh * self.price

            telemetry = {'cp_id': self.cp_id, 'conductor_id': driver_id, 'consumo_actual': round(consumed_kwh, 2), 'importe_actual': round(total_price, 2)}
            
            try:
                if self.producer:
                    self.producer.send('telemetria_cp', telemetry)
                    self.producer.flush()
                    pending_telemetry.clear()
            except Exception as e:
                pending_telemetry.append(telemetry)
                self._reconnect_kafka()
            
            time.sleep(1)

        if not self.breakdown_status:
            end_msg = {'conductor_id': driver_id, 'cp_id': self.cp_id, 'suministro_id': self.current_supply_id, 'consumo_kwh': round(consumed_kwh, 2), 'importe_total': round(total_price, 2)}
            
            try:
                self.producer.send('fin_suministro', end_msg)
                self.producer.flush()
                print(f"[FIN] Notificado a CENTRAL")
            except Exception:
                print("[ERROR] Kafka no esta diponible al finalizar el suministro")
                self._reconnect_kafka()

        with self.lock:
            self.charging = False
            self.current_driver = None
            self.current_supply_id = None

        print(f"[SUMINISTRO FINALIZADO]")
        print(f"  Consumo: {consumed_kwh:.2f} kWh")
        print(f"  Importe: {total_price:.2f} EUR")

    def start(self):
        # Esto esta mal, no tendría que enviar nada por kafka para darse de alta unicamente
        if self.producer:
            cp_init = {'cp_id': self.cp_id}
            self.producer.send('iniciar_cp', cp_init)
            self.producer.flush()

        self.thread_kafka = threading.Thread(target=self._listen_kafka, daemon=True).start()
        self.thread_monitor = threading.Thread(target=self._listen_monitor, daemon=True).start()

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
                    print("[AVERIA] Estado: AVERIA")
                elif u_input.upper() == 'R':
                    with self.lock:
                        self.breakdown_status = False
                    print("[REPARADO] Estado: OK")
                elif u_input.upper() == 'F':
                    with self.lock:
                        if self.charging:
                            self.charging = False
                            print("[FINALIZANDO] Desenchufando vehículo...")
                        else:
                            print("[ERROR] No hay suministro activo")
                elif u_input.upper().startswith('S '):
                    parts = u_input.split(maxsplit=1)
                    if len(parts) > 1:
                        driver_id = parts[1].strip()
                        with self.lock:
                            if self.charging:
                                print("[ERROR] CP ya está suministrando")
                            else:
                                print(f"[SOLICITUD] Para conductor: {driver_id}")
                                request = {'conductor_id': driver_id, 'cp_id': self.cp_id, 'origen': 'CP'}
                                try:
                                    self.producer.send('solicitudes_suministro', request)
                                    self.producer.flush()
                                except Exception:
                                    print("[ERROR] Kafka no disponible, reintentando conexión ")
                                    self._reconnect_kafka()
                    else:
                        print("[ERROR] Formato: S <DRIVER_ID>") 
                else:
                    print("[ERROR] Comando no reconocido")

            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                print(f"[ERROR] {e}")

        self.end()


    def end(self):
        print("\n[INFO] Cerrando aplicación...")
        self.running = False
        try:
            if self.thread_kafka.is_alive():
                self.thread_kafka.join(timeout=2)
            if self.thread_monitor.is_alive():
                self.thread_monitor.join(timeout=2)
        except:
            pass

        try:
            if self.consumer:
                self.consumer.close()
            if self.producer:
                self.producer.close()
            if self.monitor:
                self.monitor.close()
        except:
            pass

def main():
    if len(sys.argv) < 4:
        print("Uso: python engine.py [ip_broker:port_broker] [ip_monitor:port_monitor] <cp_id>")
        print("Ejemplo: python engine.py localhost:9092 localhost:5050 CP001")
        sys.exit(1)

    broker = sys.argv[1]
    monitor_ip, monitor_port = sys.argv[2].split(':')
    cp_id = sys.argv[3]
    
    engine = EVChargingPointEngine(broker, cp_id, monitor_ip, monitor_port)
    time.sleep(1)
    engine.start()

if __name__ == "__main__":
    main()
