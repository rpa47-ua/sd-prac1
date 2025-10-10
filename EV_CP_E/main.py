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
    msg_length = conn.recv(HEADER).decode(FORMAT)
    if msg_length:
        msg_length = int(msg_length.strip())
        return conn.recv(msg_length).decode(FORMAT)
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

        self.consumer.subscribe(['respuestas_cp'])

        self.monitor_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.monitor_server.bind((self.monitor_ip, self.monitor_port))
        self.monitor_server.listen()

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
        except Exception:
            print(f"[ERROR] monitor {addr}")
        finally:
            conn.close()

    def _listen_monitor(self):
        while self.running:
            conn, addr = self.monitor_server.accept()
            threading.Thread(target=self._handle_monitor, args=(conn, addr), daemon=True).start()

    def _send_charging_request(self, driver_id):
        print(f"[SOLICITUD] de conductor: {driver_id}")

        request = {'conductor_id': driver_id, 'cp_id': self.cp_id, 'origen': 'CP'}
        self.producer.send('solicitudes_suministro', request)

        self._wait_authorization()
        if self.charging:
            self._supply(driver_id)
            self._wait_end()

    def _listen_kafka(self):
        try:
            for msg in self.consumer:
                if not self.running or self.charging:
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
        for _ in range(timeout * 2):
            time.sleep(0.5)

    def _wait_end(self): # Repasar
        while True:
            with self.lock:
                if not self.charging:
                    break

            time.sleep(1)

    def _supply(self, driver_id):
        time_to_supply = random.randrange(2, 7) # Tiempor aleatorio entre 2 y 6 segundos
        acc_price = 0
        while time_to_supply > 0:
            acc_price += self.kWH * 100
            telemetry = {'cp_id': self.cp_id, 'conductor_id': driver_id, 'consumo_actual': self.kWH, 'importe_actual': acc_price}
            self.producer.send('telemetria_cp', telemetry)
            time_to_supply -= 1
            time.sleep(1) 

        with self.lock:
            self.charging = False

    def start(self):
        cp_init = {'cp_id': self.cp_id}
        self.producer.send('iniciar_cp', cp_init)

        print("Solicitar suministro <DRIVER_ID> | salir | A (Averia) | R (Reparar)")
        while True:
            try:
                u_input = input("> ").strip()

                if not u_input: 
                    continue
                if u_input.lower()  == 'salir':
                    break
                elif u_input == 'I':
                    self.breakdown_status = True
                elif u_input == 'R':
                    self.breakdown_status = False

                self._send_charging_request(u_input)
            except Exception:
                print("[ERROR]")


    def end(self):
        self.running = False
        time.sleep(0.5)
        self.consumer.close()
        self.producer.close()
        self.monitor_server.close()


def main():
    if len(sys.argv) < 4:
        print("Uso: python engine.py [ip_broker:port_broker] <cp_id> <monitor_port>")
        print("Ejemplo: python main.py 0.0.0.0:5055 3 5050")
        sys.exit(1)

    broker = sys.argv[1]
    cp_id = sys.argv[2]
    monitor_ip, monitor_port = sys.argv[3].split(':')
    engine = EVChargingPointEngine(broker, cp_id, monitor_ip, monitor_port)

    try:
        engine.start()
    except KeyboardInterrupt:
        print("Aplicacion interrumpida por el usuario")
    finally:
        engine.end()

if __name__ == "__main__":
    main()