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

        self.lock = threading.Lock()

        self._init_kafka()

        self.thread = threading.Thread(target=self._listen_kafka, daemon=True)
        self.thread.start()

    def _init_kafka(self):
        try:
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

            self.consumer.subscribe(['respuestas_conductor', 'telemetria_cp', 'tickets', 'notificaciones', 'fin_suministro'])

            print(f"[OK] Conectado a kafka {self.broker}")
        except Exception as e:
            print(f"[ERROR] Fallo iniciando a Kafka: {e}")
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
        
    def _send_charging_request(self, cp_id):
        with self.lock:
            if self.charging:
                print("[ERROR] Ya hay una carga en curso")
                return
            
        print(f"[SOLICITUD] en CP: {cp_id}")
        request = {'conductor_id' : self.driver_id, 'cp_id' : cp_id}
        try:
            if not self.producer:
                print("[ERRO] Kafka no disponible")
                self._reconnect_kafka()

            self.producer.send('solicitudes_suministro', request)
            self.producer.flush()
        except Exception as e:
            print(f"[ERROR] Enviar solicitud {e}")
            self._reconnect_kafka()

    def _process_message(self, topic, kmsg):
        if topic == 'respuestas_conductor' and kmsg.get('conductor_id') == self.driver_id:
            if kmsg.get('autorizado', False):
                print(f"\n[AUTORIZADO] {kmsg.get('mensaje', 'Suministro autorizado')}")
                with self.lock:
                    self.charging = True
                    self.current_cp = kmsg.get('cp_id')
                    self.last_telemetry_time = time.time()
                threading.Thread(target=self._display_stats, daemon=True).start()
            else:
                print(f"\n[DENEGADO] {kmsg.get('mensaje', 'Suministro denegado')}")

        elif topic == 'telemetria_cp' and kmsg.get('conductor_id') == self.driver_id:
            with self.lock:
                if self.charging:
                    self.current_consumption = kmsg.get('consumo_actual', 0)
                    self.current_price = kmsg.get('importe_actual', 0)
                    self.last_telemetry_time = time.time()

        elif topic == 'tickets' and kmsg.get('conductor_id') == self.driver_id:
            print(f"\n[TICKET FINAL]")
            print(f"  CP: {kmsg.get('cp_id')}")
            print(f"  Suministro ID: {kmsg.get('suministro_id')}")
            print(f"  Consumo: {kmsg.get('consumo_kwh', 0):.2f} kWh")
            print(f"  Importe: {kmsg.get('importe_total', 0):.2f} EUR")
            with self.lock:
                self.charging = False
                self.current_cp = None
                self.current_consumption = 0
                self.current_price = 0

        elif topic == 'fin_suministro' and kmsg.get('conductor_id') == self.driver_id:
            print(f"\n[FIN SUMINISTRO] CP: {kmsg.get('cp_id')}")
            with self.lock:
                self.charging = False

        elif topic == 'notificaciones' and kmsg.get('conductor_id') == self.driver_id:
            print(f"\n[NOTIFICACION] {kmsg.get('mensaje')}")
            if kmsg.get('tipo') == 'AVERIA_DURANTE_SUMINISTRO':
                with self.lock:
                    self.charging = False
                    self.current_cp = None

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
                    
            except Exception as e:
                if self.running:
                    print(f"[ERROR] Error al escuchar a Kafka: {e}")
                    time.sleep(2)
                    self._reconnect_kafka()

    def _display_stats(self):
        print(f"[SUMINISTRO EN CURSO]")
        
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
            
            if time.time() - last_data > 5:
                print(f"\n[ERROR] Sin datos de telemetría del CP {cp}.")
                print("[INFO] Finalizando suministro por inactividad...")
                with self.lock:
                    self.charging = False
                break

            print(f"\r  CP: {cp} | Tiempo: {duration}s | Consumo: {consumption:.2f} kWh | Importe: {price:.2f} EUR  ", end='', flush=True)
            time.sleep(1)
        
        print("\n")

    def _file_process(self, original_file):
        try:
            with open(original_file, 'r') as file:
                requests = [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            print(f"[ERROR] Archivo {original_file} no encontrado")
            return
        
        for i, cp_id in enumerate(requests, 1):
            print(f"\n--- Solcitud {i}/{len(requests)} ---")
            self._send_charging_request(cp_id)

            if i < len(requests):
                time.sleep(4)

    def end(self):
        print("\n[INFO] Cerrando aplicación...")
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
                self.producer.end()
        except:
            pass

    def start(self):
        print(f"=== Conductor: {self.driver_id} ===")
        print("Comandos disponibles:")
        print("  <CP_ID>  - Solicitar suministro en punto de carga")
        print("  file     - Procesar solicitudes desde suministros.txt")
        print("  salir    - Salir de la aplicación\n")

        while True:
            try: 
                u_input = input("> ").strip()

                if not u_input:
                    continue
                if u_input.lower() == 'salir':
                    break
                elif u_input.lower() == 'file':
                    self._file_process("suministros.txt")
                else:
                    self._send_charging_request(u_input.upper())
                    
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                print(f"[ERROR] {e}")
        
        self.end()

def main():
    if len(sys.argv) < 3:
        print("Uso: python main.py [ip_broker:port_broker] <driver_id>")
        print("Ejemplo: python main.py localhost:9092 DRV001")
        sys.exit(1)

    broker = sys.argv[1]
    driver_id = sys.argv[2]

    driver = EVDriver(broker, driver_id)
    time.sleep(1)
    driver.start()

if __name__ == "__main__":
    main()