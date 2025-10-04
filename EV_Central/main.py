#!/usr/bin/env python3
"""
EV_Central - Sistema Central de Gestión de Red de Carga de Vehículos Eléctricos

Uso:
    python main.py <puerto_socket> <kafka_broker> [db_host:db_port]

Ejemplo:
    python main.py 5000 localhost:9092 localhost:3306
"""
import sys
import time
import signal
from database import Database
from kafka_handler import KafkaHandler
from servidor_socket import ServidorSocket
from logica_negocio import LogicaNegocio
from panel_gui import PanelGUI


class EVCentral:
    def __init__(self, puerto_socket, kafka_broker, db_host='localhost', db_port=3306):
        self.puerto_socket = puerto_socket
        self.kafka_broker = kafka_broker
        self.db_host = db_host
        self.db_port = db_port

        # Componentes del sistema
        self.db = None
        self.kafka = None
        self.servidor = None
        self.logica = None
        self.panel = None

        self.running = False

    def inicializar(self):
        """Inicializa todos los componentes del sistema"""
        print("\n" + "=" * 60)
        print("🔋 EV_CENTRAL - Sistema de Gestión de Red de Carga")
        print("=" * 60 + "\n")

        # 1. Conectar a la base de datos
        print("📊 Conectando a la base de datos...")
        self.db = Database(
            host=self.db_host,
            port=self.db_port,
            user='evuser',
            password='evpass123',
            database='evcharging_db'
        )

        if not self.db.conectar():
            print("✗ Error crítico: No se pudo conectar a la BD")
            return False

        # 2. Inicializar Kafka
        print("\n📡 Inicializando Kafka...")
        self.kafka = KafkaHandler(self.kafka_broker)

        if not self.kafka.inicializar_producer():
            print("✗ Error crítico: No se pudo inicializar productor Kafka")
            return False

        if not self.kafka.inicializar_consumer():
            print("✗ Error crítico: No se pudo inicializar consumidor Kafka")
            return False

        # 3. Inicializar lógica de negocio
        print("\n🧠 Inicializando lógica de negocio...")
        self.logica = LogicaNegocio(self.db, self.kafka)

        # 4. Crear topics de Kafka si no existen
        print("\n📋 Creando topics de Kafka...")
        all_topics = [
            'solicitudes_suministro', 'respuestas_conductor', 'comandos_cp',
            'telemetria_cp', 'fin_suministro', 'averias', 'recuperacion_cp',
            'tickets', 'notificaciones'
        ]
        self.kafka.crear_topics_si_no_existen(all_topics)

        # 5. Configurar callbacks de Kafka
        print("\n📥 Configurando callbacks de Kafka...")
        self.kafka.registrar_callback('solicitudes_suministro', self.logica.procesar_solicitud_suministro)
        self.kafka.registrar_callback('telemetria_cp', self.logica.procesar_telemetria_cp)
        self.kafka.registrar_callback('fin_suministro', self.logica.procesar_fin_suministro)
        self.kafka.registrar_callback('averias', self.logica.procesar_averia_cp)
        self.kafka.registrar_callback('recuperacion_cp', self.logica.procesar_recuperacion_cp)

        topics = ['solicitudes_suministro', 'telemetria_cp', 'fin_suministro', 'averias', 'recuperacion_cp']
        self.kafka.suscribirse(topics)

        # 6. Iniciar servidor socket
        print(f"\n🔌 Iniciando servidor socket en puerto {self.puerto_socket}...")
        self.servidor = ServidorSocket(self.puerto_socket, self.logica.autenticar_cp)

        if not self.servidor.iniciar():
            print("✗ Error crítico: No se pudo iniciar servidor socket")
            return False

        # 7. Iniciar panel de monitorización GUI
        print("\n📺 Inicializando panel de monitorización GUI...")
        self.panel = PanelGUI(self.logica)

        print("\n" + "=" * 60)
        print("✓ SISTEMA INICIADO CORRECTAMENTE")
        print("=" * 60 + "\n")

        return True

    def ejecutar(self):
        """Ejecuta el bucle principal del sistema"""
        self.running = True

        # Iniciar consumidor de Kafka en segundo plano
        self.kafka.iniciar_consumidor_async()

        print("⚡ Sistema en funcionamiento.")
        print("📱 Abriendo panel de monitorización GUI...\n")

        # Iniciar GUI (bloqueante - usa mainloop de Tkinter)
        try:
            self.panel.iniciar()  # Esto bloquea hasta que se cierre la ventana

        except KeyboardInterrupt:
            print("\n\n⚠️ Deteniendo sistema...")

        finally:
            self.detener()

    def detener(self):
        """Detiene todos los componentes del sistema"""
        self.running = False

        if self.panel:
            self.panel.detener()

        if self.servidor:
            self.servidor.detener()

        if self.kafka:
            self.kafka.detener()

        if self.db:
            self.db.desconectar()

        print("\n✓ Sistema detenido correctamente\n")


def main():
    """Función principal"""
    if len(sys.argv) < 3:
        print("Uso: python main.py <puerto_socket> <kafka_broker> [db_host:db_port]")
        print("Ejemplo: python main.py 5000 localhost:9092 localhost:3306")
        sys.exit(1)

    puerto_socket = int(sys.argv[1])
    kafka_broker = sys.argv[2]

    # Parsear DB host y puerto (opcional)
    db_host = 'localhost'
    db_port = 3306

    if len(sys.argv) >= 4:
        db_parts = sys.argv[3].split(':')
        db_host = db_parts[0]
        if len(db_parts) > 1:
            db_port = int(db_parts[1])

    # Crear y ejecutar sistema central
    central = EVCentral(puerto_socket, kafka_broker, db_host, db_port)

    if central.inicializar():
        central.ejecutar()
    else:
        print("✗ Error al inicializar el sistema")
        sys.exit(1)


if __name__ == '__main__':
    main()
