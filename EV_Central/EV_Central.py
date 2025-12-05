# Módulo principal de EV_Central: Coordina todos los componentes del sistema central
# Inicializa BD, Kafka, servidor socket, lógica de negocio y GUI de monitorización

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

        self.db = None
        self.kafka = None
        self.servidor = None
        self.logica = None
        self.panel = None
        self.crypto = None

        self.running = False

    def inicializar(self):
        print("\n" + "=" * 60)
        print("EV_CENTRAL - Sistema de Gestion de Red de Carga")
        print("=" * 60 + "\n")

        print("Conectando a la base de datos...")
        self.db = Database(
            host=self.db_host,
            port=self.db_port,
            user='evuser',
            password='evpass123',
            database='evcharging_db'
        )

        if not self.db.conectar():
            print("[ERROR] Error critico: No se pudo conectar a la BD")
            return False

        print("\nInicializando sistema de cifrado simétrico...")
        self.crypto = CryptoManager(self.db)
        print("[OK] CryptoManager inicializado")

        print("\nMarcando todos los CPs como desconectados...")
        self.db.marcar_todos_cps_desconectados()

        print("\nInicializando Kafka...")
        self.kafka = KafkaHandler(self.kafka_broker, self.crypto)

        if not self.kafka.inicializar_producer():
            print("[ERROR] Error critico: No se pudo inicializar productor Kafka")
            return False

        if not self.kafka.inicializar_consumer():
            print("[ERROR] Error critico: No se pudo inicializar consumidor Kafka")
            return False

        print(f"\nIniciando servidor socket en puerto {self.puerto_socket}...")
        self.servidor = ServidorSocket(
            self.puerto_socket,
            None,
            None,
            None
        )

        if not self.servidor.iniciar():
            print("[ERROR] Error critico: No se pudo iniciar servidor socket")
            return False

        print("\nInicializando logica de negocio...")
        self.logica = LogicaNegocio(self.db, self.kafka, self.servidor)

        self.servidor.callback_autenticacion = self.logica.autenticar_cp
        self.servidor.callback_desconexion = self.logica.manejar_desconexion_monitor
        self.servidor.callback_estado = self.logica.procesar_estado_engine

        print("\nCreando topics de Kafka...")
        all_topics = [
            'solicitudes_suministro', 'respuestas_conductor', 'respuestas_cp',
            'comandos_cp', 'telemetria_cp', 'fin_suministro', 'averias',
            'recuperacion_cp', 'tickets', 'notificaciones', 'estado_cps',
            'registro_conductores', 'solicitud_estado_engine', 
            'respuesta_estado_engine', 'estado_central', 'errores_cifrado'
        ]
        self.kafka.crear_topics_si_no_existen(all_topics)

        print("\nConfigurando callbacks de Kafka...")
        self.kafka.registrar_callback('solicitudes_suministro', self.logica.procesar_solicitud_suministro)
        self.kafka.registrar_callback('telemetria_cp', self.logica.procesar_telemetria_cp)
        self.kafka.registrar_callback('fin_suministro', self.logica.procesar_fin_suministro)
        self.kafka.registrar_callback('averias', self.logica.procesar_averia_cp)
        self.kafka.registrar_callback('recuperacion_cp', self.logica.procesar_recuperacion_cp)
        self.kafka.registrar_callback('estado_cps', self.logica.procesar_solicitud_listado)
        self.kafka.registrar_callback('registro_conductores', self.logica.procesar_registro_conductor)
        self.kafka.registrar_callback('respuesta_estado_engine', self.logica.procesar_respuesta_estado_engine)
        self.kafka.registrar_callback('errores_cifrado', self.logica.procesar_error_cifrado)

        topics = ['solicitudes_suministro', 'telemetria_cp', 'fin_suministro', 'averias', 'recuperacion_cp', 'estado_cps', 'registro_conductores', 'respuesta_estado_engine','errores_cifrado']
        self.kafka.suscribirse(topics)

        print("\nRecuperando suministros del sistema...")
        self.logica.recuperar_suministros_al_inicio()

        print("\nVerificando claves de cifrado para CPs existentes...")
        cps = self.db.obtener_todos_los_cps()
        for cp in cps:
            cp_id = cp['id']
            if not cp.get('clave_cifrado'):
                print(f"[CRYPTO] Generando clave para CP {cp_id} sin clave...")
                self.crypto.generar_clave_para_cp(cp_id)

        print("\nInicializando panel de monitorizacion GUI...")
        self.panel = PanelGUI(self.logica)

        print("\n" + "=" * 60)
        print("SISTEMA INICIADO CORRECTAMENTE")
        print("=" * 60 + "\n")

        self.kafka.producer.send('estado_central', key=b'central', value={'estado': True})
        self.kafka.producer.flush

        return True

    def ejecutar(self):
        self.running = True

        self.kafka.iniciar_consumidor_async()

        print("Sistema en funcionamiento.")
        print("[INFO] Los Monitores se reconectarán automáticamente y enviarán sus estados actuales")
        print("Abriendo panel de monitorizacion GUI...\n")

        try:
            self.panel.iniciar()

        except KeyboardInterrupt:
            print("\n\nDeteniendo sistema...")

        finally:
            self.detener()

    def detener(self):
        self.running = False

        # Enviar estado de cierre a Kafka (sin esperar respuesta si falla)
        try:
            if self.kafka and self.kafka.producer:
                self.kafka.producer.send('estado_central', key=b'central', value={'estado': False})
                self.kafka.producer.flush()
        except:
            pass  # Ignorar errores al cerrar

        # Detener panel GUI
        if self.panel:
            try:
                self.panel.detener()
            except:
                pass

        # Detener servidor socket
        if self.servidor:
            try:
                self.servidor.detener()
            except:
                pass

        # Detener Kafka
        if self.kafka:
            try:
                self.kafka.detener()
            except:
                pass

        # Desconectar BD
        if self.db:
            try:
                self.db.desconectar()
            except:
                pass

        print("\nSistema detenido correctamente\n")


def main():
    if len(sys.argv) < 3:
        print("Uso: python EV_Central.py <puerto_socket> <kafka_broker> [db_host:db_port]")
        print("Ejemplo: python EV_Central.py 5000 localhost:9092 localhost:3306")
        sys.exit(1)

    puerto_socket = int(sys.argv[1])
    kafka_broker = sys.argv[2]

    db_host = 'localhost'
    db_port = 3306

    if len(sys.argv) >= 4:
        db_parts = sys.argv[3].split(':')
        db_host = db_parts[0]
        if len(db_parts) > 1:
            db_port = int(db_parts[1])

    central = EVCentral(puerto_socket, kafka_broker, db_host, db_port)

    if central.inicializar():
        central.ejecutar()
    else:
        print("[ERROR] Error al inicializar el sistema")
        sys.exit(1)


if __name__ == '__main__':
    main()
