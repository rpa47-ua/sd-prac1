import sys
import json
import time
import threading
from kafka import KafkaProducer, KafkaConsumer

class EVDriver:
    def __init__(self, broker, id_driver):
        self.broker = broker
        self.id_driver = id_driver
        self.charging = False
        self.running = True # control para los threads
        self.lock = threading.Lock()

        # Inicializamos kafka, productor y consumidor:

        self.producer = KafkaProducer(
            bootstrap_servers = self.broker,
            value_serializer = lambda v: json.dumps(v).encode('utf-8')
        ) #broker, codificacion dict --> bytes

        self.consumer = KafkaConsumer(
            bootstrap_servers = self.broker,
            value_deserializer = lambda m: json.loads(m.decode('utf-8'))
        ) #broker, decodificacion bytes --> dict

        self.consumer.subscribe(['respuestas_conductor', 'telemtria_cp', 'tickets', 'notificaciones'])

        self.thread = threading.Thread(target=self._charge, daemon=True)
        self.thread.start()
        
    def _charging_request(self, cp_id):
        print(f"[SOLICITUD] en CP: {cp_id}")

        request = {'conductor_id' : self.id_driver, 'cp_id' : cp_id}
        self.producer.send('solicitudes_suministro', request) #topic, message

        self._wait_authorization()
        if self.charging:
            self._wait_end()

    def _charge(self):
        #Procesamiento de los mensajes de KAFKA

        try:
            for msg in self.consumer:
                if not self.running:
                    break

                response = msg.value

                if msg.topic == 'respuestas_conductor' and response.get('conductor_id') == self.id_driver:
                    if response.get('autorizado', False): # i, j --> Default
                        print(f"[AUTORIZADO] {response.get('mensaje')}")
                        with self.lock:
                            self.charging = True
                    else:
                        print(f"[DENGADO] {response.get('mensaje')}")

                elif msg.topic == 'telemtria_cp' and response.get('conductor_id') == self.id_driver:
                    with self.lock:
                        if self.charging and response.get('conductor_id') == self.id_driver:
                            print(f"[TELEMETRIA] CP: {response.get('cp_id')}: {response.get('consumo_actual')} kWh | {response.get('importe_actual')} EUR")
                
                elif msg.topic == 'tickets' and response.get('conductor_id') == self.id_driver:
                    print(f"[TICKET] CP: {response.get('cp_id')} | SUMINISTRO ID {response.get('suministro_id')}")
                    print(f"[TICKET] CONSUMO: {response.get('consumo_kwh')} | IMPORTE TOTAL {response.get('importe_total')} EUR")
                    with self.lock:
                        self.charging = False

                elif msg.topic == 'notificaciones' and response.get('conductor_id') == self.id_driver:
                    print(f"[NOTIFICACION] {response.get('mensaje')}")
                    if response.get('tipo') == 'AVERIA_DURANTE_SUMINISTRO':
                        with self.lock:
                            self.charging = False
                
                ## Listas cps??
        except Exception:
            print("[ERROR]")
                    
    def _wait_authorization(self, timeout=10): # Repasar
        for _ in range(timeout * 2):
            time.sleep(0.5)

    def _wait_end(self): # Repasar
        while True:
            with self.lock:
                    if not self.charging:
                        break

            time.sleep(1)

    def _file_process(self, original_file):
        try:
            with open(original_file, 'r') as file:
                requests = [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            print(f"[ERROR] Archivo {original_file} no encontrado")
            return
        
        for i, cp_id in enumerate(requests, 1):
            self._charging_request(cp_id)

            if i < len(requests):
                time.sleep(4)

    def end(self):
        self.running = False
        time.sleep(0.5) # dar tiempo para que el hilo termine
        self.consumer.close()
        self.producer.close()

    def start(self):
        print(f"Conductor: {self.id_driver}")
        print("<CP_ID> | file | salir\n")

        while True:
            try: 
                uInput = input("> ").strip()

                if not uInput:
                    continue
                if uInput.lower() == 'salir':
                    break
                elif uInput.lower() == 'file':
                    self._file_process("suministros.txt")
                
                self._charging_request(uInput.upper())
            except Exception:
                print("[ERROR]")

def main():
    if len(sys.argv) < 3:
        print("Uso: python main.py [ip_broker:port_broker] <id_driver>")
        sys.exit(1)
    
    broker = sys.argv[1]
    id_driver = sys.argv[2]

    driver = EVDriver(broker, id_driver)
    time.sleep(1) ### ???
    try:
        driver.start()
    except KeyboardInterrupt:
        print("Aplicacion interrumpida por el usuario")
    finally:
        driver.end()

if __name__ == "__main__":
    main()