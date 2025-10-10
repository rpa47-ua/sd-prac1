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
        self.running = True # control para los threads
        self.lock = threading.Lock() # para variable compartida charging

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

        self.thread = threading.Thread(target=self._listen_kafka, daemon=True)
        self.thread.start()
        
    def _send_charging_request(self, cp_id):
        print(f"[SOLICITUD] en CP: {cp_id}")

        request = {'conductor_id' : self.driver_id, 'cp_id' : cp_id}
        self.producer.send('solicitudes_suministro', request) #topic, message

        self._wait_authorization()
        if self.charging:
            self._wait_end()

    def _listen_kafka(self):
        #Procesamiento de los mensajes de KAFKA

        try:
            for msg in self.consumer:
                if not self.running:
                    break

                kmsg = msg.value

                if msg.topic == 'respuestas_conductor' and kmsg.get('conductor_id') == self.driver_id:
                    if kmsg.get('autorizado', False): # i, j --> Default
                        print(f"[AUTORIZADO] {kmsg.get('mensaje')}")
                        with self.lock:
                            self.charging = True
                    else:
                        print(f"[DENGADO] {kmsg.get('mensaje')}")

                elif msg.topic == 'telemetria_cp' and kmsg.get('conductor_id') == self.driver_id:
                    with self.lock:
                        if self.charging and kmsg.get('conductor_id') == self.driver_id:
                            print(f"[TELEMETRIA] CP: {kmsg.get('cp_id')}: {kmsg.get('consumo_actual')} kWh | {kmsg.get('importe_actual')} EUR")
                
                elif msg.topic == 'tickets' and kmsg.get('conductor_id') == self.driver_id:
                    print(f"[TICKET] CP: {kmsg.get('cp_id')} | SUMINISTRO ID {kmsg.get('suministro_id')}")
                    print(f"[TICKET] CONSUMO: {kmsg.get('consumo_kwh')} | IMPORTE TOTAL {kmsg.get('importe_total')} EUR")
                    with self.lock:
                        self.charging = False

                elif msg.topic == 'notificaciones' and kmsg.get('conductor_id') == self.driver_id:
                    print(f"[NOTIFICACION] {kmsg.get('mensaje')}")
                    if kmsg.get('tipo') == 'AVERIA_DURANTE_SUMINISTRO':
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
            self._send_charging_request(cp_id)

            if i < len(requests):
                time.sleep(4)

    def end(self):
        self.running = False
        time.sleep(0.5) # dar tiempo para que el hilo termine
        self.consumer.close()
        self.producer.close()

    def start(self):
        print(f"Conductor: {self.driver_id}")
        print("Solicitar suministro <CP_ID> | file | salir\n")

        while True:
            try: 
                u_input = input("> ").strip()

                if not u_input:
                    continue
                if u_input.lower() == 'salir':
                    break
                elif u_input.lower() == 'file':
                    self._file_process("suministros.txt")
                
                self._send_charging_request(u_input.upper())
            except Exception:
                print("[ERROR]")

def main():
    if len(sys.argv) < 3:
        print("Uso: python main.py [ip_broker:port_broker] <driver_id>")
        print("Ejemplo: python main.py 0.0.0.0:192.168.56.88 3")
        sys.exit(1)
    
    broker = sys.argv[1]
    driver_id = sys.argv[2]

    driver = EVDriver(broker, driver_id)
    time.sleep(1) ### ???
    try:
        driver.start()
    except KeyboardInterrupt:
        print("Aplicacion interrumpida por el usuario")
    finally:
        driver.end()

if __name__ == "__main__":
    main()