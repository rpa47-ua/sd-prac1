# Módulo de gestión de Kafka: Maneja productores y consumidores de mensajes
# Incluye reconexión automática y callbacks para procesar mensajes por topic

from kafka import KafkaProducer, KafkaConsumer
from kafka.admin import KafkaAdminClient, NewTopic
from json import dumps, loads
import threading
import base64


class KafkaHandler:
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.consumer = None
        self.running = False
        self.callbacks = {}
        self.crypto = crypto_manager


    def crear_topics_si_no_existen(self, topics: list):
        try:
            admin_client = KafkaAdminClient(bootstrap_servers=self.bootstrap_servers)

            existing_topics = admin_client.list_topics()

            new_topics = [
                NewTopic(name=topic, num_partitions=1, replication_factor=1)
                for topic in topics if topic not in existing_topics
            ]

            if new_topics:
                admin_client.create_topics(new_topics=new_topics, validate_only=False)
                print(f"[OK] Topics creados: {', '.join([t.name for t in new_topics])}")
            else:
                print("[OK] Todos los topics ya existen")

            admin_client.close()
            return True
        except Exception as e:
            print(f"[AVISO] No se pudieron crear topics automaticamente: {e}")
            print("  Los topics se crearan automaticamente al enviar mensajes")
            return True

    def inicializar_producer(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: dumps(v).encode('utf-8')
            )
            print(f"[OK] Productor Kafka inicializado en {self.bootstrap_servers}")
            return True
        except Exception as e:
            print(f"[ERROR] Error inicializando productor Kafka: {e}")
            return False

    def inicializar_consumer(self, group_id: str = 'ev_central_group'):
        try:
            self.consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                value_deserializer=lambda m: loads(m.decode('utf-8'))
            )
            print(f"[OK] Consumidor Kafka inicializado")
            return True
        except Exception as e:
            print(f"[ERROR] Error inicializando consumidor Kafka: {e}")
            return False

    def suscribirse(self, topics: list):
        if self.consumer:
            self.consumer.subscribe(topics)
            print(f"[OK] Suscrito a topics: {', '.join(topics)}")

def enviar_mensaje(self, topic: str, mensaje: dict, cp_id: str = None, reintentar=True):
    """
    Envía un mensaje a Kafka, opcionalmente cifrado para un CP específico
    """
    if not self.producer:
        print("[ERROR] Productor no inicializado")
        if reintentar:
            print("[KAFKA] Intentando reinicializar productor...")
            if self.inicializar_producer():
                return self.enviar_mensaje(topic, mensaje, cp_id, reintentar=False)
        return False

    try:
        
        mensaje_final = mensaje.copy()
        if cp_id and self.crypto:
            mensaje_cifrado = self.crypto.cifrar_mensaje(cp_id, mensaje)
            if mensaje_cifrado:
                mensaje_cifrado_b64 = base64.b64encode(mensaje_cifrado).decode('utf-8')
                mensaje_final = {
                    'cifrado': True,
                    'cp_id': cp_id,
                    'data': mensaje_cifrado_b64
                }
                print(f"[KAFKA-CIFRADO] Mensaje cifrado enviado a {topic} para CP {cp_id}")
            else:
                print(f"[CRYPTO] Error cifrando mensaje para {cp_id}, enviando sin cifrar")
                mensaje_final['cifrado_error'] = True
        
        self.producer.send(topic, mensaje_final)
        self.producer.flush()
        return True
        
    except Exception as e:
        print(f"[ERROR] Error enviando mensaje a {topic}: {e}")

def procesar_mensaje_recibido(self, mensaje: dict):
    """
    Procesa un mensaje recibido de Kafka, descifrándolo si es necesario
    """
   
    
    error_cifrado = False
    cp_id = mensaje.get('cp_id')
    
    if mensaje.get('cifrado') and cp_id and self.crypto:
        try:
            data_cifrada = mensaje.get('data')
            if data_cifrada:
                mensaje_cifrado = base64.b64decode(data_cifrada)
                
                mensaje_descifrado = self.crypto.descifrar_mensaje(cp_id, mensaje_cifrado)
                
                if mensaje_descifrado:
                    print(f"[KAFKA-CIFRADO] Mensaje descifrado de CP {cp_id}")
                    return mensaje_descifrado, cp_id, False
                else:
                    print(f"[ERROR-CIFRADO] No se pudo descifrar mensaje de CP {cp_id}")
                    error_cifrado = True
            else:
                print(f"[ERROR-CIFRADO] Mensaje cifrado sin datos: {mensaje}")
                error_cifrado = True
        except Exception as e:
            print(f"[ERROR-CIFRADO] Error procesando mensaje cifrado de {cp_id}: {e}")
            error_cifrado = True
    
    return mensaje, cp_id, error_cifrado

    def registrar_callback(self, topic: str, callback_func):
        self.callbacks[topic] = callback_func

    def iniciar_consumidor_async(self):
        self.running = True
        thread = threading.Thread(target=self._consumir_mensajes, daemon=True)
        thread.start()
        print("[OK] Consumidor Kafka ejecutandose en segundo plano")

def _consumir_mensajes(self):
    import time
    reconexion_intentos = 0
    max_intentos_consecutivos = 5

    while self.running:
        try:
            mensajes = self.consumer.poll(timeout_ms=1000)

            reconexion_intentos = 0

            for topic_partition, records in mensajes.items():
                for record in records:
                    topic = record.topic
                    mensaje = record.value
                    mensaje_procesado, cp_id, error_cifrado = self.procesar_mensaje_recibido(mensaje)
                    
                    if error_cifrado:
                        mensaje_procesado['cifrado_error'] = True
                    
                    if topic in self.callbacks:
                        self.callbacks[topic](mensaje_procesado) 
                    else:
                        print(f"[AVISO] Mensaje recibido de {topic} sin callback: {mensaje_procesado}")

            except Exception as e:
                print(f"[ERROR] Error consumiendo mensajes de Kafka: {e}")
                reconexion_intentos += 1

                if reconexion_intentos <= max_intentos_consecutivos:
                    print(f"[KAFKA] Intento de reconexión {reconexion_intentos}/{max_intentos_consecutivos}...")
                    time.sleep(2)

                    try:
                        if self.consumer:
                            try:
                                self.consumer.close()
                            except:
                                pass

                        self.inicializar_consumer()

                        if self.consumer and self.callbacks:
                            topics = list(self.callbacks.keys())
                            self.suscribirse(topics)
                            print("[KAFKA] Reconexión exitosa!")
                            reconexion_intentos = 0
                    except Exception as reconex_error:
                        print(f"[ERROR] Fallo en reconexión: {reconex_error}")
                else:
                    print(f"[ERROR] Máximo de intentos alcanzado. Esperando 10 segundos...")
                    time.sleep(10)
                    reconexion_intentos = 0

    def detener(self):
        self.running = False
        try:
            if self.producer:
                self.producer.flush()
                self.producer.close()
        except:
            pass
        try:
            if self.consumer:
                self.consumer.close()
        except:
            pass
        print("[OK] Kafka handler detenido")