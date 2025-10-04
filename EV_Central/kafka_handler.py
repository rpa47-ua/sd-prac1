"""
Módulo de gestión de Kafka para EV_Central
Maneja productores y consumidores de mensajes
"""
from confluent_kafka import Producer, Consumer, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic
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
            admin_client = AdminClient({'bootstrap.servers': self.bootstrap_servers})

            # Obtener topics existentes
            metadata = admin_client.list_topics(timeout=5)
            existing_topics = set(metadata.topics.keys())

            # Crear nuevos topics
            new_topics = [
                NewTopic(topic, num_partitions=1, replication_factor=1)
                for topic in topics if topic not in existing_topics
            ]

            if new_topics:
                fs = admin_client.create_topics(new_topics)
                for topic, f in fs.items():
                    try:
                        f.result()
                        print(f"✓ Topic '{topic}' creado")
                    except Exception as e:
                        print(f"⚠ Topic '{topic}': {e}")
            else:
                print("✓ Todos los topics ya existen")

            return True
        except Exception as e:
            print(f"⚠ No se pudieron crear topics automáticamente: {e}")
            print("  Los topics se crearán automáticamente al enviar mensajes")
            return True  # No es error crítico

    def inicializar_producer(self):
        """Inicializa el productor de Kafka"""
        try:
            self.producer = Producer({
                'bootstrap.servers': self.bootstrap_servers,
                'client.id': 'ev_central_producer'
            })
            print(f"✓ Productor Kafka inicializado en {self.bootstrap_servers}")
            return True
        except Exception as e:
            print(f"✗ Error inicializando productor Kafka: {e}")
            return False

    def inicializar_consumer(self, group_id: str = 'ev_central_group'):
        """Inicializa el consumidor de Kafka"""
        try:
            self.consumer = Consumer({
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': group_id,
                'auto.offset.reset': 'latest',
                'enable.auto.commit': True
            })
            print(f"✓ Consumidor Kafka inicializado")
            return True
        except Exception as e:
            print(f"✗ Error inicializando consumidor Kafka: {e}")
            return False

    def suscribirse(self, topics: list):
        """Suscribe el consumidor a una lista de topics"""
        if self.consumer:
            self.consumer.subscribe(topics)
            print(f"✓ Suscrito a topics: {', '.join(topics)}")

    def enviar_mensaje(self, topic: str, mensaje: dict):
        """Envía un mensaje a un topic de Kafka"""
        if not self.producer:
            print("✗ Productor no inicializado")
            return False

        try:
            self.producer.produce(
                topic,
                value=dumps(mensaje).encode('utf-8'),
                callback=self._delivery_callback
            )
            self.producer.poll(0)
            return True
        except Exception as e:
            print(f"✗ Error enviando mensaje a {topic}: {e}")
            return False

    def _delivery_callback(self, err, msg):
        """Callback para confirmar entrega de mensajes"""
        if err:
            print(f"✗ Error en entrega: {err}")
        # else:
        #     print(f"✓ Mensaje entregado a {msg.topic()}")

    def registrar_callback(self, topic: str, callback_func):
        """Registra una función callback para procesar mensajes de un topic"""
        self.callbacks[topic] = callback_func

    def iniciar_consumidor_async(self):
        """Inicia el consumidor en un hilo separado"""
        self.running = True
        thread = threading.Thread(target=self._consumir_mensajes, daemon=True)
        thread.start()
        print("✓ Consumidor Kafka ejecutándose en segundo plano")

    def _consumir_mensajes(self):
        """Bucle de consumo de mensajes (ejecutado en hilo separado)"""
        while self.running:
            try:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                if msg.error():
                    print(f"✗ Error Kafka: {msg.error()}")
                    continue

                # Decodificar mensaje
                topic = msg.topic()
                mensaje = loads(msg.value().decode('utf-8'))

                # Ejecutar callback correspondiente
                if topic in self.callbacks:
                    self.callbacks[topic](mensaje)
                else:
                    print(f"⚠ Mensaje recibido de {topic} sin callback: {mensaje}")

            except Exception as e:
                print(f"✗ Error consumiendo mensaje: {e}")

    def detener(self):
        """Detiene el consumidor y cierra conexiones"""
        self.running = False
        if self.producer:
            self.producer.flush()
        if self.consumer:
            self.consumer.close()
        print("✓ Kafka handler detenido")
