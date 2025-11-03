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
    def __init__(self, broker, cp_id, monitor_ip, monitor_port, gui_mode=False):
        self.broker = broker
        self.cp_id = cp_id
        self.monitor_ip = monitor_ip
        self.monitor_port = int(monitor_port)
        self.gui_mode = gui_mode
        self.gui = None

        self.breakdown_status = False
        self.charging = False
        self.running = True
        self.current_driver = None
        self.current_supply_id = None

        self.kWH = abs(1 - random.random())
        self.price = abs(1 - random.random())

        self.lock = threading.Lock()
        self.print_lock = threading.Lock()

        self.producer = None
        self.consumer = None
        self._init_kafka()
        self._init_monitor()

    ### KAFKA
    
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

            self.consumer.subscribe(['respuestas_cp', 'respuestas_conductor', 'solicitud_estado_engine'])
            self._log("OK", f"Conectado a Kafka en {self.broker}")
        except Exception:
            self._log("ERROR", "No se pudo establecer conexión con Kafka. Verifique el broker o la red.")
            self.producer = None
            self.consumer = None

    def _reconnect_kafka(self):
        while self.running:
            self._log("INFO", "Intentando reconexión con Kafka...")
            try:
                self._init_kafka()
                if self.producer and self.consumer:
                    self._log("OK", "Reconexión con Kafka completada.")
                    return
            except Exception:
                self._log("ERROR", "Intento de reconexión a Kafka fallido.")
            time.sleep(5)

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
                        if msg.topic == 'solicitud_estado_engine':
                            self._handle_estado_solicitud(kmsg)
                        elif msg.topic in ['respuestas_cp', 'respuestas_conductor'] and kmsg.get('cp_id') == self.cp_id:
                            self._handle_authorization_response(kmsg)
            except Exception:
                self._log("ERROR", "Error al recibir mensajes de Kafka.")
                self._reconnect_kafka()
                time.sleep(2)

    ### MONITOR

    def _init_monitor(self):
        try:
            self.monitor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.monitor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.monitor.bind((self.monitor_ip, self.monitor_port))
            self.monitor.listen(5)
            self.monitor.settimeout(1)
            self._log("OK", f"Servidor de monitor activo en {self.monitor_ip}:{self.monitor_port}")
        except Exception:
            self._log("ERROR", "No se pudo iniciar el servidor del monitor.")
            self.monitor = None

    def _handle_monitor(self, conn, addr):
        self._log("INFO", f"Monitor conectado desde {addr[0]}:{addr[1]}")
        try:
            while self.running:
                msg = recv(conn)
                if not msg:
                    break
                if msg == "STATUS?":
                    with self.lock:
                        if self.breakdown_status:
                            status = "AVERIA"
                        elif self.charging:
                            status = "SUMINISTRANDO"
                        else:
                            status = "OK"
                    send(status, conn)
        except Exception:
            self._log("ERROR", f"Problema con el monitor {addr}")
        finally:
            try:
                conn.close()
            except:
                pass
            self._log("INFO", f"Monitor desconectado: {addr[0]}:{addr[1]}")

    def _listen_monitor(self):
        while self.running:
            if not self.monitor:
                time.sleep(2)
                continue
            try:
                conn, addr = self.monitor.accept()
                threading.Thread(target=self._handle_monitor, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                if self.running:
                    self._log("ERROR", "Fallo en la conexión con el monitor.")
                    time.sleep(1)

    ### SUMINISTRO Y FUNCIONALIDADES

    def _handle_estado_solicitud(self, kmsg):
        """Responde a solicitud de Central con el estado actual del suministro"""
        if kmsg.get('tipo') == 'SOLICITAR_ESTADO':
            with self.lock:
                if self.charging and self.current_driver and self.current_supply_id:
                    # Calcular estado actual
                    consumo = self.kWH
                    importe = consumo * self.price

                    respuesta = {
                        'cp_id': self.cp_id,
                        'activo': True,
                        'conductor_id': self.current_driver,
                        'suministro_id': self.current_supply_id,
                        'consumo_actual': round(consumo, 3),
                        'importe_actual': round(importe, 2)
                    }
                    self._log("INFO", f"Enviando estado de suministro activo a Central")
                else:
                    respuesta = {
                        'cp_id': self.cp_id,
                        'activo': False
                    }
                    self._log("INFO", f"No hay suministro activo para reportar")

                try:
                    self.producer.send('respuesta_estado_engine', respuesta)
                    self.producer.flush()
                except Exception:
                    self._log("ERROR", "No se pudo enviar respuesta de estado")

    def _handle_authorization_response(self, kmsg):
        if kmsg.get('autorizado', False):
            self._log("OK", f"Suministro autorizado para conductor {kmsg.get('conductor_id')}.")
            with self.lock:
                if self.charging:
                    return
                self.charging = True
                self.current_driver = kmsg.get('conductor_id')
                self.current_supply_id = kmsg.get('suministro_id')
                threading.Thread(target=self._supply, daemon=True).start()
                threading.Thread(target=self._display_stats, daemon=True).start()
        else:
            self._log("ERROR", f"Suministro denegado: {kmsg.get('mensaje', 'Autorización rechazada.')}")

    def _notify_breakdown(self, driver_id):
        try:
            msg = {
                'tipo': 'AVERIA_DURANTE_SUMINISTRO',
                'conductor_id': driver_id,
                'cp_id': self.cp_id,
                'mensaje': 'Suministro interrumpido por avería'
            }
            self.producer.send('notificaciones', msg)
            self.producer.flush()
            self._log("EVENTO", "Avería comunicada a la central y al conductor.")
        except Exception:
            self._log("ERROR", "No se pudo notificar la avería. Intentando reconexión Kafka.")
            self._reconnect_kafka()

    def _supply(self):
        with self.lock:
            driver_id = self.current_driver
            supply_id = self.current_supply_id

        self._log("EVENTO", f"Suministro iniciado | Conductor {driver_id} | ID {supply_id} | Precio {self.price:.2f} €/kWh")

        consumed_kwh = 0
        total_price = 0

        while True:
            with self.lock:
                if not self.charging or not self.running:
                    break
                if self.breakdown_status:
                    self._log("EVENTO", "Avería detectada. Suministro interrumpido.")
                    self._notify_breakdown(driver_id)
                    self.charging = False
                    break

            consumed_kwh += self.kWH
            total_price = consumed_kwh * self.price
            
            telemetry = {
                'cp_id': self.cp_id,
                'conductor_id': driver_id,
                'consumo_actual': round(consumed_kwh, 2),
                'importe_actual': round(total_price, 2)
            }

            try:
                if self.producer:
                    self.producer.send('telemetria_cp', telemetry)
                    self.producer.flush()
            except Exception:
                pass

            time.sleep(1)

        if not self.breakdown_status:
            end_msg = {
                'conductor_id': driver_id,
                'cp_id': self.cp_id,
                'suministro_id': self.current_supply_id,
                'consumo_kwh': round(consumed_kwh, 2),
                'importe_total': round(total_price, 2)
            }
            try:
                if self.producer:
                    self.producer.send('fin_suministro', end_msg)
                    self.producer.flush()
                    self._log("OK", "Fin de suministro comunicado a la central.")
            except Exception:
                self._log("ERROR", "No se pudo comunicar el fin de suministro.")

        with self.lock:
            self.charging = False
            self.current_driver = None
            self.current_supply_id = None

        self._log("EVENTO", f"Suministro finalizado. Consumo total {consumed_kwh:.2f} kWh | Total {total_price:.2f} EUR")


    ### UTILIDAD

    def _log(self, level, msg, end="\n"):
        with self.print_lock:
            print(f"\n[{level}] {msg}", end=end, flush=True)

    def _display_stats(self):
        start_time = time.time()
        consumed_kwh = 0
        total_price = 0

        while True:
            with self.lock:
                if not self.charging:
                    break
                consumed_kwh += self.kWH
                total_price = consumed_kwh * self.price
                driver = self.current_driver
                cp = self.cp_id

            duration = int(time.time() - start_time)
            
            with self.print_lock:
                print(
                    f"\rCP {cp} | Conductor {driver} | Tiempo {duration}s | "
                    f"Consumo {consumed_kwh:.2f} kWh | Total {total_price:.2f} EUR",
                    end='', flush=True
                )
            
            if self.gui_mode and self.gui and hasattr(self.gui, '_update_metrics'):
                try:
                    if hasattr(self.gui, 'root') and self.gui.root.winfo_exists():
                        self.gui.root.after(0, lambda c=consumed_kwh, p=total_price, d=duration: 
                                           self.gui._update_metrics(c, p, d))
                except:
                    pass
            
            time.sleep(1)
            
        with self.print_lock:
            print()

    ### ENGINE

    def start(self):
        threading.Thread(target=self._listen_kafka, daemon=True).start()
        threading.Thread(target=self._listen_monitor, daemon=True).start()

        if self.gui_mode:
            self._start_with_gui()
        else:
            self._start_cli()

    def _start_with_gui(self):
        try:
            from gui import EVChargingGUI
            self.gui = EVChargingGUI(self)
            
            cli_thread = threading.Thread(target=self._start_cli, daemon=True)
            cli_thread.start()
            
            try:
                self.gui.run()
            except:
                pass
        except ImportError:
            print("\n[ERROR] No se pudo importar el módulo GUI. Asegúrese de que gui.py existe.")
            print("[INFO] Cambiando a modo CLI...\n")
            self.gui_mode = False
            self._start_cli()
        except Exception as e:
            print(f"\n[ERROR] Error al iniciar GUI: {e}")
            print("[INFO] Cambiando a modo CLI...\n")
            self.gui_mode = False
            self._start_cli()

    def _start_cli(self):
        if self.gui_mode:
            time.sleep(0.5)
            
        self._log("OK", f"Punto de carga {self.cp_id} operativo.\n")
        print("=== MENÚ DE COMANDOS ===")
        print("  S <ID_CONDUCTOR>  → Solicitar suministro")
        print("  F                 → Finalizar suministro actual")
        print("  A                 → Simular avería")
        print("  R                 → Reparar avería")
        print("  SALIR             → Cerrar la aplicación")
        print("=========================\n")

        while self.running:
            try:
                cmd = input().strip()
                if not cmd:
                    continue

                if cmd.upper() == 'SALIR':
                    if self.gui_mode and self.gui:
                        try:
                            self.gui.root.after(0, self.gui.root.destroy)
                        except:
                            pass
                    break
                elif cmd.upper() == 'A':
                    with self.lock:
                        self.breakdown_status = True
                    self._log("EVENTO", "Estado cambiado: AVERÍA simulada.")
                elif cmd.upper() == 'R':
                    with self.lock:
                        self.breakdown_status = False
                    self._log("OK", "Estado cambiado: punto de carga reparado.")
                elif cmd.upper() == 'F':
                    with self.lock:
                        if self.charging:
                            self.charging = False
                            self._log("EVENTO", "Finalizando suministro actual...")
                        else:
                            self._log("INFO", "No hay suministro activo para finalizar.")
                elif cmd.upper().startswith('S '):
                    parts = cmd.split(maxsplit=1)
                    if len(parts) > 1:
                        driver_id = parts[1].strip()
                        with self.lock:
                            if self.charging:
                                self._log("INFO", "El punto de carga ya está suministrando energía.")
                            else:
                                self._log("EVENTO", f"Solicitud de suministro enviada para conductor {driver_id}.")
                                request = {'conductor_id': driver_id, 'cp_id': self.cp_id, 'origen': 'CP'}
                                try:
                                    self.producer.send('solicitudes_suministro', request)
                                    self.producer.flush()
                                except Exception:
                                    self._log("ERROR", "Kafka no disponible. Reintentando conexión.")
                                    self._reconnect_kafka()
                    else:
                        self._log("ERROR", "Formato incorrecto. Use: S <ID_CONDUCTOR>")
                else:
                    self._log("INFO", "Comando no reconocido.")
            except (EOFError, KeyboardInterrupt):
                if self.gui_mode and self.gui:
                    try:
                        self.gui.root.after(0, self.gui.root.destroy)
                    except:
                        pass
                break
            except Exception:
                self._log("ERROR", "Error interno al procesar el comando.")
        
        if not self.gui_mode:
            self.end()

    def end(self):
        self._log("INFO", "Cerrando aplicación...")
        
        # Si hay suministro activo, finalizarlo
        with self.lock:
            if self.charging and self.current_driver and self.current_supply_id:
                driver_id = self.current_driver
                supply_id = self.current_supply_id
                self._log("INFO", "Finalizando suministro activo antes de cerrar...")
                self.charging = False
        
        # Dar tiempo para que se complete el suministro
        time.sleep(2)
        
        self.running = False
        try:
            if self.consumer:
                self.consumer.close()
            if self.producer:
                self.producer.close()
            if self.monitor:
                self.monitor.close()
        except:
            pass
        self._log("OK", "Aplicación finalizada correctamente.")


def main():
    if len(sys.argv) < 4:
        print("Uso: python main.py [ip_broker:port_broker] [ip_monitor:port_monitor] <cp_id> [--gui]")
        print("Ejemplo CLI: python main.py localhost:9092 localhost:5050 CP001")
        print("Ejemplo GUI: python main.py localhost:9092 localhost:5050 CP001 --gui")
        sys.exit(1)

    broker = sys.argv[1]
    monitor_ip, monitor_port = sys.argv[2].split(':')
    cp_id = sys.argv[3]
    
    gui_mode = '--gui' in sys.argv or '-g' in sys.argv

    engine = EVChargingPointEngine(broker, cp_id, monitor_ip, monitor_port, gui_mode=gui_mode)
    time.sleep(1)
    engine.start()


if __name__ == "__main__":
    main()