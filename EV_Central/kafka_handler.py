"""
Módulo de gestión de Kafka para EV_Central
Maneja productores y consumidores de mensajes
"""
from kafka import KafkaProducer, KafkaConsumer
from kafka.admin import KafkaAdminClient, NewTopic
from json import dumps, loads
import threading


class KafkaHandler:
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.consumer = None
        self.running = False
        self.callbacks = {}

    def crear_topics_si_no_existen(self, topics: list):
        """Crea los topics de Kafka si no existen"""
        try:
            admin_client = KafkaAdminClient(bootstrap_servers=self.bootstrap_servers)

            # Obtener topics existentes
            existing_topics = admin_client.list_topics()

            # Crear nuevos topics
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
            return True  # No es error critico

    def inicializar_producer(self):
        """Inicializa el productor de Kafka"""
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
        """Inicializa el consumidor de Kafka"""
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
        """Suscribe el consumidor a una lista de topics"""
        if self.consumer:
            self.consumer.subscribe(topics)
            print(f"[OK] Suscrito a topics: {', '.join(topics)}")

    def enviar_mensaje(self, topic: str, mensaje: dict, reintentar=True):
        """Envia un mensaje a un topic de Kafka con reconexión automática"""
        if not self.producer:
            print("[ERROR] Productor no inicializado")
            if reintentar:
                print("[KAFKA] Intentando reinicializar productor...")
                if self.inicializar_producer():
                    return self.enviar_mensaje(topic, mensaje, reintentar=False)
            return False

        try:
            self.producer.send(topic, mensaje)
            self.producer.flush()
            return True
        except Exception as e:
            print(f"[ERROR] Error enviando mensaje a {topic}: {e}")

            # Intentar reconectar el productor
            if reintentar:
                print("[KAFKA] Intentando reconectar productor...")
                import time
                time.sleep(1)

                try:
                    if self.producer:
                        try:
                            self.producer.close()
                        except:
                            pass

                    if self.inicializar_producer():
                        print("[KAFKA] Productor reconectado, reintentando envío...")
                        return self.enviar_mensaje(topic, mensaje, reintentar=False)
                except Exception as reconex_error:
                    print(f"[ERROR] Fallo reconectando productor: {reconex_error}")

            return False

    def registrar_callback(self, topic: str, callback_func):
        """Registra una funcion callback para procesar mensajes de un topic"""
        self.callbacks[topic] = callback_func

    def iniciar_consumidor_async(self):
        """Inicia el consumidor en un hilo separado"""
        self.running = True
        thread = threading.Thread(target=self._consumir_mensajes, daemon=True)
        thread.start()
        print("[OK] Consumidor Kafka ejecutandose en segundo plano")

    def _consumir_mensajes(self):
        """Bucle de consumo de mensajes (ejecutado en hilo separado)"""
        import time
        reconexion_intentos = 0
        max_intentos_consecutivos = 5

        while self.running:
            try:
                # Poll por mensajes (timeout de 1 segundo)
                mensajes = self.consumer.poll(timeout_ms=1000)

                # Si el poll fue exitoso, resetear contador de reconexiones
                reconexion_intentos = 0

                for topic_partition, records in mensajes.items():
                    for record in records:
                        topic = record.topic
                        mensaje = record.value

                        # Ejecutar callback correspondiente
                        if topic in self.callbacks:
                            self.callbacks[topic](mensaje)
                        else:
                            print(f"[AVISO] Mensaje recibido de {topic} sin callback: {mensaje}")

            except Exception as e:
                print(f"[ERROR] Error consumiendo mensajes de Kafka: {e}")
                reconexion_intentos += 1

                # Intentar reconectar
                if reconexion_intentos <= max_intentos_consecutivos:
                    print(f"[KAFKA] Intento de reconexión {reconexion_intentos}/{max_intentos_consecutivos}...")
                    time.sleep(2)

                    try:
                        # Reintentar inicializar consumer
                        if self.consumer:
                            try:
                                self.consumer.close()
                            except:
                                pass

                        self.inicializar_consumer()

                        # Re-suscribirse a los topics
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
                    reconexion_intentos = 0  # Resetear para reintentar

    def detener(self):
        """Detiene el consumidor y cierra conexiones"""
        self.running = False
        if self.producer:
            self.producer.flush()
        if self.consumer:
            self.consumer.close()
        print("[OK] Kafka handler detenido")
