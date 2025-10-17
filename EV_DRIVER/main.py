import sys
import json
import time
import threading
from kafka import KafkaProducer, KafkaConsumer

class EVDriver:
    def __init__(self, broker, driver_id):
        self.broker = broker
        self.driver_id = driver_id

        self.charging = False
        self.running = True
        self.current_cp = None
        self.current_consumption = 0
        self.current_price = 0
        self.last_telemetry_time = 0
        self.cps_disponibles = {}

        self.lock = threading.Lock()

        self._init_kafka()

        self.thread = threading.Thread(target=self._listen_kafka, daemon=True)
        self.thread.start()

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
                self._init_kafka()
                if self.producer and self.consumer:
                    print("[OK] Reconexión con Kafka completada\n")
                    return
            except:
                print("[ERROR] No se pudo reconectar con Kafka. Se volverá a intentar...\n")
            time.sleep(5)
        
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
            self._reconnect_kafka()

    def _process_message(self, topic, kmsg):
        if topic == 'respuestas_conductor' and kmsg.get('conductor_id') == self.driver_id:
            if kmsg.get('autorizado', False):
                print(f"\n[AUTORIZADO] {kmsg.get('mensaje', 'Suministro autorizado')}\n")
                with self.lock:
                    if self.charging: # Por si cae central para no volve a _display_stats
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
            cp_id = kmsg.get('cp_id')
            estado = kmsg.get('estado')
            with self.lock:
                self.cps_disponibles[cp_id] = estado

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

    def _display_stats(self):
        print("\n[SUMINISTRO EN CURSO]\n")
        start_time = time.time()
        
        while True:
            with self.lock:
                if not self.charging:
                    break
                cp = self.current_cp
                consumption = self.current_consumption
                price = self.current_price
                last_data = self.last_telemetry_time
            
            duration = int(time.time() - start_time)
            
            if time.time() - last_data > 10:
                print(f"\n[ERROR] No se reciben datos de telemetría del CP {cp}.\n"
                      f"[INFO] Finalizando suministro por inactividad...\n")
                with self.lock:
                    self.charging = False
                break

            print(f"\r  CP: {cp} | Tiempo: {duration}s | Consumo: {consumption:.2f} kWh | Importe: {price:.2f} EUR  ", 
                  end='', flush=True)
            time.sleep(1)
        
        print("\n")

    def _file_process(self, original_file):
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

    def end(self):
        print("\n[INFO] Cerrando aplicación...\n")
        self.running = False
        
        try:
            self.consumer.wakeup()
        except:
            pass
            
        if self.thread.is_alive():
            self.thread.join(timeout=2)
        
        try:
            if self.consumer:
                self.consumer.end()
            if self.producer:
                self.producer.close()
        except:
            pass

    def _mostrar_cps_disponibles(self):
        with self.lock:
            if not self.cps_disponibles:
                print("\n[INFO] No hay puntos de carga registrados aún.\n")
                return

            print("\n=== PUNTOS DE CARGA ===")

            for cp_id, estado in sorted(self.cps_disponibles.items()):
                if estado == 'desconectado':
                    continue
                elif estado == 'activado':
                    print(f"  ✓ {cp_id:<10} - Disponible")
                elif estado == 'suministrando':
                    print(f"  ⊗ {cp_id:<10} - Suministrando")
                elif estado == 'averiado':
                    print(f"  ✗ {cp_id:<10} - Averiado")
                elif estado == 'parado':
                    print(f"  ⊗ {cp_id:<10} - Parado")
                else:
                    print(f"  ? {cp_id:<10} - {estado.capitalize()}")

            print("=" * 35 + "\n")

    def start(self):
        print(f"=== Conductor: {self.driver_id} ===\n")
        print("Comandos disponibles:\n"
              "  <CP_ID>  - Solicitar suministro en punto de carga\n"
              "  lista    - Ver puntos de carga disponibles\n"
              "  file     - Procesar solicitudes desde suministros.txt\n"
              "  salir    - Salir de la aplicación\n")

        while True:
            try:
                u_input = input("> ").strip()

                if not u_input:
                    continue
                if u_input.lower() == 'salir':
                    break
                elif u_input.lower() == 'lista':
                    self._mostrar_cps_disponibles()
                elif u_input.lower() == 'file':
                    self._file_process("suministros.txt")
                else:
                    self._send_charging_request(u_input.upper())
                    
            except (EOFError, KeyboardInterrupt):
                break
            except Exception:
                print("\n[ERROR] Se produjo un error inesperado al procesar el comando.\n")
        
        self.end()

def main():
    if len(sys.argv) < 3:
        print("\nUso: python main.py [ip_broker:port_broker] <driver_id>\n"
              "Ejemplo: python main.py localhost:9092 DRV001\n")
        sys.exit(1)

    broker = sys.argv[1]
    driver_id = sys.argv[2]

    driver = EVDriver(broker, driver_id)
    time.sleep(1)
    driver.start()

if __name__ == "__main__":
    main()