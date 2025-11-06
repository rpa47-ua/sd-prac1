import sys
import json
import time
import threading
from kafka import KafkaProducer, KafkaConsumer

class EVDriver:
    def __init__(self, broker, driver_id, gui_mode=False):
        self.broker = broker
        self.driver_id = driver_id
        self.gui_mode = gui_mode
        self.gui = None

        self.charging = False
        self.running = True
        self.current_cp = None
        self.current_consumption = 0
        self.current_price = 0
        self.last_telemetry_time = 0
        self.cp_list = {}
        self.waiting_authorization = False
        self.file_processing = False
        self.file_requests = []
        self.file_index = 0
        self.central_status = False

        self.lock = threading.Lock()
        self.print_lock = threading.Lock()

        self.display_running = False # tELEMETRIA
        self._status_active = False
        self._status_text = ""
        self._status_length = 0

        self.producer = None
        self.consumer = None
        self._init_kafka()
        self._driver_register()

        self.thread = threading.Thread(target=self._listen_kafka, daemon=True)
        self.thread.start()

    ### LOG DE MENSAJES 

    def _log(self, level, msg, status=False, end="\n"):
        with self.print_lock:
            if status:
                text = f"\r{msg}"
                self._status_active = True
                self._status_text = text
                self._status_length = len(msg)
                sys.stdout.write(text)
                sys.stdout.flush()
            else:
                if self._status_active and level in ['TICKET', 'FIN SUMINISTRO', 'NOTIFICACIÓN']:
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                    self._status_active = False
                elif self._status_active:
                    sys.stdout.write('\r' + ' ' * self._status_length + '\r')
                    sys.stdout.flush()
                    self._status_active = False

                print(f"[{level}] {msg}", end=end, flush=True)

                if self._status_active and level not in ['TICKET', 'FIN SUMINISTRO', 'NOTIFICACIÓN']:
                    sys.stdout.write(self._status_text)
                    sys.stdout.flush()

    ### KAFKA

    def _driver_register(self):
        if self.producer:
            try:
                registro = {
                    'tipo': 'CONECTAR',
                    'conductor_id': self.driver_id
                }
                self.producer.send('registro_conductores', registro)
                self.producer.flush()
                time.sleep(3)
                self._log("REGISTRO", f"Conductor {self.driver_id} registrado en el sistema")

                recuperacion = {
                    'tipo': 'RECUPERAR_SUMINISTRO',
                    'conductor_id': self.driver_id
                }
                self.producer.send('registro_conductores', recuperacion)
                self.producer.flush()
                time.sleep(2)
            except Exception as e:
                self._log("ERROR", f"No se pudo registrar el conductor: {e}")

    def _init_kafka(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.broker,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            self.consumer = KafkaConsumer(
                bootstrap_servers=self.broker,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id=f'driver_{self.driver_id}',
                auto_offset_reset='latest',
                enable_auto_commit=True
            )

            self.consumer.subscribe(['respuestas_conductor', 'telemetria_cp', 'tickets', 'notificaciones', 'fin_suministro', 'estado_cps', 'estado_central'])

            self._log("OK", f"Conectado a Kafka en {self.broker}")

            try:
                tmp_consumer = KafkaConsumer(
                    'estado_central',
                    bootstrap_servers=self.broker,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='earliest',
                    enable_auto_commit=False,
                    consumer_timeout_ms=500 
                )
                for msg in tmp_consumer:
                    if msg.key == b'central':
                        self.central_status = msg.value.get('estado', False)
                        break

                tmp_consumer.close()

            except Exception:
                self._log("ERROR", "No se pudo leer el estado inicial de la Central.")
                
        except Exception:
            self._log("ERROR", "No se pudo iniciar la conexión con Kafka. Verifique el broker y vuelva a intentarlo.")
            self.producer = None
            self.consumer = None

    def _reconnect_kafka(self):
        while self.running:
            self._log("INFO", "Reintentando conexión con Kafka...")
            try:
                if self.consumer:
                    self.consumer.close()
                if self.producer:
                    self.producer.close()

                self._init_kafka()
                if self.producer and self.consumer:
                    self._log("OK", "Reconexión con Kafka completada")
                    return
            except:
                self._log("ERROR", "No se pudo reconectar con Kafka. Se volverá a intentar...")
            time.sleep(5)

    def _listen_kafka(self):
        while self.running:
            try:
                if not self.consumer:
                    self._reconnect_kafka()
                    time.sleep(2)
                    continue

                records = self.consumer.poll(timeout_ms=1000)
                for tp, msgs in records.items():
                    for msg in msgs:
                        self._process_message(msg.topic, msg.value)
                    
            except Exception:
                if self.running:
                    self._log("ERROR", "Se produjo un problema al escuchar los mensajes de Kafka.")
                    time.sleep(2)
                    self._reconnect_kafka()
        
    ### SUMINISTRO Y FUNCIONALIDADES

    def _send_charging_request(self, cp_id, time_to_end=None):
        with self.lock:
            if not self.central_status:
                self._log("ERROR", "Imposible conectar con la Central")
                return
            if self.charging or self.waiting_authorization:
                self._log("ERROR", "Ya existe una carga en curso o esperando autorización. Espere a que finalice antes de iniciar otra.")
                return
            
        self._log("SOLICITUD", f"Enviando solicitud de carga al punto de carga: {cp_id}")
        if time_to_end:
            self._log("INFO", f"  Tiempo límite solicitado: {time_to_end}s")
        
        request = {
            'conductor_id': self.driver_id, 
            'cp_id': cp_id
        }

        if time_to_end is not None:
            request['time_to_end'] = time_to_end   

        try:
            if not self.producer:
                self._log("ERROR", "Kafka no está disponible. Intentando reconexión...")
                self._reconnect_kafka()
                return

            with self.lock:
                self.waiting_authorization = True
                
            self.producer.send('solicitudes_suministro', request)
            self.producer.flush()
            self._log("OK", "Solicitud enviada correctamente.")
        except Exception:
            self._log("ERROR", "No se pudo enviar la solicitud al broker Kafka.")
            with self.lock:
                self.waiting_authorization = False

    def _file_process(self, original_file):
        self._log("INFO", "Verificando registro del conductor...")
        time.sleep(3)

        try:
            with open(original_file, 'r') as file:
                requests = []
                for line in file:
                    parts = line.strip().split()
                    if not parts:
                        continue
                    cp_id = parts[0]
                    time_to_end = float(parts[1]) if len(parts) > 1 and parts[1].replace('.', '', 1).isdigit() else None
                    requests.append((cp_id, time_to_end))
        except FileNotFoundError:
            self._log("ERROR", f"No se encontró el archivo {original_file}. Verifique el nombre o la ruta.")
            return

        with self.lock:
            self.file_processing = True
            self.file_requests = requests
            self.file_index = 0

        self._log("INFO", f"Procesando {len(requests)} solicitudes secuencialmente...")
        self._process_next_file_request()

    def _process_next_file_request(self):
        with self.lock:
            if not self.file_processing:
                return

            if self.file_index >= len(self.file_requests):
                self._log("INFO", "Todas las solicitudes del archivo han sido procesadas.")
                self.file_processing = False
                return

            cp_id, time_to_end  = self.file_requests[self.file_index]
            request_num = self.file_index + 1
            total = len(self.file_requests)

        self._log("INFO", f"--- Procesando solicitud {request_num}/{total} ---")

        while True:
            with self.lock:
                if not self.charging and not self.waiting_authorization:
                    break
            self._log("INFO", f"Esperando a que termine el suministro actual antes de procesar solicitud {request_num}/{total}...")
            time.sleep(2)

        self._send_charging_request(cp_id, time_to_end)

    def _display_stats(self):
        if self.gui_mode:
            return
                
        start_time = time.time()
        self.display_running = True
        
        while self.display_running:
            with self.lock:
                if not self.charging:
                    break
                cp = self.current_cp
                consumption = self.current_consumption
                price = self.current_price
                last_data = self.last_telemetry_time
            
            if not cp:
                break
                
            if time.time() - last_data > 2:
                self._log("INFO", "Finalizando suministro por averia") # REPASAR
                with self.lock:
                    self.charging = False
                break

            status_text = f"CP: {cp} | Consumo: {consumption:.2f} kWh | Importe: {price:.2f} EUR"
            self._log("", status_text, status=True)
            time.sleep(0.5)

        self.display_running = False

    
    def _list_cps(self):
        with self.lock:
            if not self.cp_list:
                self._log("INFO", "No hay puntos de carga registrados aún.")
                return

            self._log("INFO", "=== PUNTOS DE CARGA ===")
            for cp_id, estado in sorted(self.cp_list.items()):
                if estado == 'activado':
                    print(f"{cp_id:<10} - Disponible")
                elif estado == 'suministrando':
                    print(f"{cp_id:<10} - Suministrando")
                elif estado == 'averiado':
                    print(f"{cp_id:<10} - Averiado")
                elif estado == 'parado':
                    print(f"{cp_id:<10} - Parado")
                else:
                    print(f"{cp_id:<10} - {estado.capitalize()}")
            self._log("INFO", "========================")

    def _request_cp_list(self):
        with self.lock:
            self.cp_list.clear()
        request = {'tipo': 'SOLICITUD'}
        try:
            if not self.producer:
                self._log("ERROR", "Intentando reconexión a Kafka")
                self._reconnect_kafka()
                return

            self.producer.send('estado_cps', request)
            self.producer.flush()
            self._log("SOLICITUD", "Petición de listado de puntos de carga enviada.")

            wait_time = 0
            while not self.cp_list and wait_time < 3:
                time.sleep(1)
                wait_time += 0.2

        except Exception:
            self._log("ERROR", "No se pudo enviar la solicitud al broker Kafka.")

    ### UTILIDAD 

    def _process_message(self, topic, kmsg):
        if topic == "estado_central":
            with self.lock:
                self.central_status = kmsg.get('estado', False)
        elif topic == 'respuestas_conductor' and kmsg.get('conductor_id') == self.driver_id:
            if kmsg.get('autorizado', False):
                self._log("AUTORIZADO", f"{kmsg.get('mensaje', 'Suministro autorizado')}")
                with self.lock:
                    if self.charging:
                        self.waiting_authorization = False
                        return 
                    
                    self.charging = True
                    self.waiting_authorization = False
                    self.current_cp = kmsg.get('cp_id')
                    self.last_telemetry_time = time.time()
                threading.Thread(target=self._display_stats, daemon=True).start()
            else:
                mensaje = kmsg.get('mensaje', 'Suministro denegado')
                self._log("DENEGADO", f"{mensaje}")

                en_cola = 'En cola' in mensaje

                with self.lock:
                    if en_cola:
                        self._log("INFO", "Permaneciendo en cola. Esperando autorización...")
                    else:
                        self.waiting_authorization = False
                        if self.file_processing:
                            self.file_index += 1
                            threading.Thread(target=self._process_next_file_request, daemon=True).start()

        elif topic == 'telemetria_cp' and kmsg.get('conductor_id') == self.driver_id:
            with self.lock:
                self.current_consumption = kmsg.get('consumo_actual', 0)
                self.current_price = kmsg.get('importe_actual', 0)
                self.last_telemetry_time = time.time()

        elif topic == 'tickets' and kmsg.get('conductor_id') == self.driver_id:
            self._log("TICKET", f"CP: {kmsg.get('cp_id')} | Suministro ID: {kmsg.get('suministro_id')} | Consumo: {kmsg.get('consumo_kwh', 0):.2f} kWh | Importe: {kmsg.get('importe_total', 0):.2f} EUR")
            with self.lock:
                self.charging = False
                self.current_cp = None
                self.current_consumption = 0
                self.current_price = 0

                if self.file_processing:
                    self.file_index += 1
                    time.sleep(4)
                    threading.Thread(target=self._process_next_file_request, daemon=True).start()

        elif topic == 'fin_suministro' and kmsg.get('conductor_id') == self.driver_id:
            self._log("FIN SUMINISTRO", f"Finalizado en CP: {kmsg.get('cp_id')}")
            with self.lock:
                self.charging = False

        elif topic == 'notificaciones' and kmsg.get('conductor_id') == self.driver_id:
            self._log("NOTIFICACIÓN", f"{kmsg.get('mensaje')}")
            if kmsg.get('tipo') == 'AVERIA_DURANTE_SUMINISTRO':
                with self.lock:
                    self.charging = False
                    self.current_cp = None
                    self.current_consumption = 0
                    self.current_price = 0
                    
                    if self.file_processing:
                        self.file_index += 1
                        threading.Thread(target=self._process_next_file_request, daemon=True).start()

        elif topic == 'estado_cps':
            tipo = kmsg.get('tipo')
            if tipo == 'ESTADO_CP':
                cp_id = kmsg.get('cp_id')
                estado = kmsg.get('estado')
                with self.lock:
                    self.cp_list[cp_id] = estado
                
                if self.gui_mode and self.gui and hasattr(self.gui, '_update_cp_list'):
                    try:
                        if hasattr(self.gui, 'root') and self.gui.root.winfo_exists():
                            self.gui.root.after(0, self.gui._update_cp_list)
                    except:
                        pass

    ### DRIVER

    def start(self):
        if self.gui_mode:
            self._start_with_gui()
        else:
            self._start_cli()

    def _start_with_gui(self):
        try:
            from gui import EVDriverGUI
            self.gui = EVDriverGUI(self)
            
            cli_thread = threading.Thread(target=self._start_cli, daemon=True)
            cli_thread.start()
            
            try:
                self.gui.run()
            except:
                pass
        except ImportError:
            self._log("ERROR", "No se pudo importar el módulo GUI. Asegúrese de que driver_gui.py existe.")
            self._log("INFO", "Cambiando a modo CLI...")
            self.gui_mode = False
            self._start_cli()
        except Exception as e:
            self._log("ERROR", f"Error al iniciar GUI: {e}")
            self._log("INFO", "Cambiando a modo CLI...")
            self.gui_mode = False
            self._start_cli()

    def _start_cli(self):
        if self.gui_mode:
            time.sleep(0.5)
            
        self._log("OK", f"Conductor {self.driver_id} operativo.")
        self._log("INFO", "=== MENÚ DE COMANDOS ===")
        self._log("INFO", "S <CP_ID>     - Solicitar suministro en punto de carga")
        self._log("INFO", "lista         - Ver puntos de carga disponibles")
        self._log("INFO", "file          - Procesar solicitudes desde suministros.txt")
        self._log("INFO", "file <nombre> - Procesar solicitudes desde archivo específico")
        self._log("INFO", "salir         - Salir de la aplicación")
        self._log("INFO", "========================")

        while self.running:
            try:
                cmd = input().strip()
                if not cmd:
                    continue
                if cmd.lower() == 'salir':
                    if self.gui_mode and self.gui:
                        try:
                            self.gui.root.after(0, self.gui.root.destroy)
                        except:
                            pass
                    break
                elif cmd.lower() == 'lista':
                    self._request_cp_list()
                    self._list_cps()
                elif cmd.lower() == 'file':
                    self._file_process("suministros.txt")
                elif cmd.lower().startswith('file '):
                    parts = cmd.split(maxsplit=1)
                    if len(parts) > 1:
                        filename = parts[1].strip()
                        self._file_process(filename)
                    else:
                        self._log("ERROR", "Formato incorrecto. Use: file <nombre_archivo>")
                elif cmd.upper().startswith('S '):
                    parts = cmd.split(maxsplit=1)
                    if len(parts) > 1:
                        driver_id = parts[1].strip()
                        self._send_charging_request(driver_id)
                    else:
                        self._log("ERROR", "Formato incorrecto. Use: S <CP_ID>")
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
                self._log("ERROR", "Se produjo un error inesperado al procesar el comando.")
        
        if not self.gui_mode:
            self.end()

    def end(self):
        self._log("INFO", "Cerrando aplicación...")

        if self.producer:
            try:
                desregistro = {
                    'tipo': 'DESCONECTAR',
                    'conductor_id': self.driver_id
                }
                self.producer.send('registro_conductores', desregistro)
                self.producer.flush()
                time.sleep(2)
                self._log("DESREGISTRO", f"Conductor {self.driver_id} desconectado del sistema")
            except Exception as e:
                self._log("ERROR", f"No se pudo desregistrar el conductor: {e}")

        self.running = False

        try:
            self.consumer.wakeup()
        except:
            pass

        if self.thread.is_alive():
            self.thread.join(timeout=2)

        try:
            if self.consumer:
                self.consumer.close()
            if self.producer:
                self.producer.close()
        except:
            pass


def main():
    if len(sys.argv) < 3:
        print("\nUso: python main.py [ip_broker:port_broker] <driver_id> [--gui]")
        print("Ejemplo CLI: python EV_Driver.py localhost:9092 DRV001")
        print("Ejemplo GUI: python EV_Driver.py localhost:9092 DRV001 --gui")
        sys.exit(1)

    broker = sys.argv[1]
    driver_id = sys.argv[2]
    
    gui_mode = '--gui' in sys.argv or '-g' in sys.argv

    driver = EVDriver(broker, driver_id, gui_mode=gui_mode)
    time.sleep(1)
    driver.start()

if __name__ == "__main__":
    main()