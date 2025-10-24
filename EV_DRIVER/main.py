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

        self.lock = threading.Lock()

        self._init_kafka()
        self._registrar_conductor()

        self.thread = threading.Thread(target=self._listen_kafka, daemon=True)
        self.thread.start()

    ### KAFKA

    def _registrar_conductor(self):
        """Registra el conductor en el sistema al iniciar"""
        if self.producer:
            try:
                registro = {
                    'tipo': 'CONECTAR',
                    'conductor_id': self.driver_id
                }
                self.producer.send('registro_conductores', registro)
                self.producer.flush()
                time.sleep(3)
                print(f"[REGISTRO] Conductor {self.driver_id} registrado en el sistema\n")

                # Solicitar recuperación de suministro activo
                recuperacion = {
                    'tipo': 'RECUPERAR_SUMINISTRO',
                    'conductor_id': self.driver_id
                }
                self.producer.send('registro_conductores', recuperacion)
                self.producer.flush()
                time.sleep(2)
            except Exception as e:
                print(f"[ERROR] No se pudo registrar el conductor: {e}\n")

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

            self.consumer.subscribe(['respuestas_conductor', 'telemetria_cp', 'tickets', 'notificaciones', 'fin_suministro', 'estado_cps'])

            print(f"\n[OK] Conectado a Kafka en {self.broker}\n")
        except Exception:
            print("\n[ERROR] No se pudo iniciar la conexión con Kafka. Verifique el broker y vuelva a intentarlo.\n")
            self.producer = None
            self.consumer = None

    def _reconnect_kafka(self):
        while self.running:
            print("\n[INFO] Reintentando conexión con Kafka...\n")
            try:
                if self.consumer:
                    self.consumer.close()
                if self.producer:
                    self.producer.close()

                self._init_kafka()
                if self.producer and self.consumer:
                    print("[OK] Reconexión con Kafka completada\n")
                    return
            except:
                print("[ERROR] No se pudo reconectar con Kafka. Se volverá a intentar...\n")
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
                    print("\n[ERROR] Se produjo un problema al escuchar los mensajes de Kafka.\n")
                    time.sleep(2)
                    self._reconnect_kafka()
        
    ### SUMINISTRO Y FUNCIONALIDADES

    def _send_charging_request(self, cp_id):
        with self.lock:
            if self.charging:
                print("\n[ERROR] Ya existe una carga en curso. Espere a que finalice antes de iniciar otra.\n")
                return
            
        print(f"\n[SOLICITUD] Enviando solicitud de carga al punto de carga: {cp_id}\n")
        
        request = {
            'conductor_id': self.driver_id, 
            'cp_id': cp_id
        }

        try:
            if not self.producer:
                print("\n[ERROR] Kafka no está disponible. Intentando reconexión...\n")
                self._reconnect_kafka()
                return

            self.producer.send('solicitudes_suministro', request)
            self.producer.flush()
            print("[OK] Solicitud enviada correctamente.\n")
        except Exception:
            print("\n[ERROR] No se pudo enviar la solicitud al broker Kafka.\n")

    def _file_process(self, original_file):
        # Esperar a que el registro esté completo
        print("\n[INFO] Verificando registro del conductor...\n")
        time.sleep(3)

        try:
            with open(original_file, 'r') as file:
                requests = [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            print(f"\n[ERROR] No se encontró el archivo {original_file}. Verifique el nombre o la ruta.\n")
            return

        for i, cp_id in enumerate(requests, 1):
            print(f"\n--- Procesando solicitud {i}/{len(requests)} ---\n")
            self._send_charging_request(cp_id)

            if i < len(requests):
                time.sleep(4)

    def _display_stats(self):
        if self.gui_mode:
            return
            
        print("\n[SUMINISTRO EN CURSO]\n")
        start_time = time.time()
        
        while True:
            with self.lock:
                if not self.charging:
                    return
                cp = self.current_cp
                consumption = self.current_consumption
                price = self.current_price
                last_data = self.last_telemetry_time
            
            duration = int(time.time() - start_time)
            
            if time.time() - last_data > 5:
                print(f"\n[ERROR] No se reciben datos de telemetría del CP {cp}.\n"
                      f"[INFO] Finalizando suministro por inactividad...\n")
                with self.lock:
                    self.charging = False
                break

            print(f"\r  CP: {cp} | Tiempo: {duration}s | Consumo: {consumption:.2f} kWh | Importe: {price:.2f} EUR  ", 
                  end='', flush=True)
            time.sleep(1)
        
        print("\n")

    
    def _list_cps(self):
        with self.lock:
            if not self.cp_list:
                print("\n[INFO] No hay puntos de carga registrados aún.\n")
                return

            print("\n=== PUNTOS DE CARGA ===")
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
            print("=" * 23 + "\n")

    def _request_cp_list(self):
        request = {'tipo': 'SOLICITUD'}
        try:
            if not self.producer:
                print("[ERROR] Intentando reconexión a Kafka")
                self._reconnect_kafka()
                return

            self.producer.send('estado_cps', request)
            self.producer.flush()
            print("\n[SOLICITUD] Petición de listado de puntos de carga enviada.\n")

            wait_time = 0
            while not self.cp_list and wait_time < 3:
                time.sleep(0.2)
                wait_time += 0.2

        except Exception:
            print("\n[ERROR] No se pudo enviar la solicitud al broker Kafka.\n")

    ### UTILIDAD 

    def _process_message(self, topic, kmsg):
        if topic == 'respuestas_conductor' and kmsg.get('conductor_id') == self.driver_id:
            if kmsg.get('autorizado', False):
                print(f"\n[AUTORIZADO] {kmsg.get('mensaje', 'Suministro autorizado')}\n")
                with self.lock:
                    if self.charging:
                        return 
                    
                    self.charging = True
                    self.current_cp = kmsg.get('cp_id')
                    self.last_telemetry_time = time.time()
                threading.Thread(target=self._display_stats, daemon=True).start()
            else:
                print(f"\n[DENEGADO] {kmsg.get('mensaje', 'Suministro denegado')}\n")

        elif topic == 'telemetria_cp' and kmsg.get('conductor_id') == self.driver_id:
            with self.lock:
                if self.charging:
                    self.current_consumption = kmsg.get('consumo_actual', 0)
                    self.current_price = kmsg.get('importe_actual', 0)
                    self.last_telemetry_time = time.time()

        elif topic == 'tickets' and kmsg.get('conductor_id') == self.driver_id:
            print(f"\n[TICKET FINAL]\n"
                  f"  CP: {kmsg.get('cp_id')}\n"
                  f"  Suministro ID: {kmsg.get('suministro_id')}\n"
                  f"  Consumo: {kmsg.get('consumo_kwh', 0):.2f} kWh\n"
                  f"  Importe: {kmsg.get('importe_total', 0):.2f} EUR\n")
            with self.lock:
                self.charging = False
                self.current_cp = None
                self.current_consumption = 0
                self.current_price = 0

        elif topic == 'fin_suministro' and kmsg.get('conductor_id') == self.driver_id:
            print(f"\n[FIN SUMINISTRO] Finalizado en CP: {kmsg.get('cp_id')}\n")
            with self.lock:
                self.charging = False

        elif topic == 'notificaciones' and kmsg.get('conductor_id') == self.driver_id:
            print(f"\n[NOTIFICACIÓN] {kmsg.get('mensaje')}\n")
            if kmsg.get('tipo') == 'AVERIA_DURANTE_SUMINISTRO':
                with self.lock:
                    self.charging = False
                    self.current_cp = None
                    self.current_consumption = 0
                    self.current_price = 0

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
            print("\n[ERROR] No se pudo importar el módulo GUI. Asegúrese de que driver_gui.py existe.")
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
            
        print(f"=== Conductor: {self.driver_id} ===\n")
        print("Comandos disponibles:\n"
              "  <CP_ID>  - Solicitar suministro en punto de carga\n"
              "  lista    - Ver puntos de carga disponibles\n"
              "  file     - Procesar solicitudes desde suministros.txt\n"
              "  salir    - Salir de la aplicación\n")

        while self.running:
            try:
                u_input = input("> ").strip()

                if not u_input:
                    continue
                if u_input.lower() == 'salir':
                    if self.gui_mode and self.gui:
                        try:
                            self.gui.root.after(0, self.gui.root.destroy)
                        except:
                            pass
                    break
                elif u_input.lower() == 'lista':
                    self._request_cp_list()
                    self._list_cps()
                elif u_input.lower() == 'file':
                    self._file_process("suministros.txt")
                else:
                    self._send_charging_request(u_input.upper())
                    
            except (EOFError, KeyboardInterrupt):
                if self.gui_mode and self.gui:
                    try:
                        self.gui.root.after(0, self.gui.root.destroy)
                    except:
                        pass
                break
            except Exception:
                print("\n[ERROR] Se produjo un error inesperado al procesar el comando.\n")
        
        if not self.gui_mode:
            self.end()

    def end(self):
        print("\n[INFO] Cerrando aplicación...\n")

        # Desregistrar conductor ANTES de cambiar running a False
        if self.producer:
            try:
                desregistro = {
                    'tipo': 'DESCONECTAR',
                    'conductor_id': self.driver_id
                }
                self.producer.send('registro_conductores', desregistro)
                self.producer.flush()
                time.sleep(2)
                print(f"[DESREGISTRO] Conductor {self.driver_id} desconectado del sistema\n")
            except Exception as e:
                print(f"[ERROR] No se pudo desregistrar el conductor: {e}\n")

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
        print("\nUso: python main.py [ip_broker:port_broker] <driver_id> [--gui]\n"
              "Ejemplo CLI: python main.py localhost:9092 DRV001\n"
              "Ejemplo GUI: python main.py localhost:9092 DRV001 --gui\n")
        sys.exit(1)

    broker = sys.argv[1]
    driver_id = sys.argv[2]
    
    gui_mode = '--gui' in sys.argv or '-g' in sys.argv

    driver = EVDriver(broker, driver_id, gui_mode=gui_mode)
    time.sleep(1)
    driver.start()

if __name__ == "__main__":
    main()