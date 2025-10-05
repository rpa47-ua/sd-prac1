"""
Lógica de negocio para EV_Central
Contiene las reglas y validaciones del sistema
"""


class LogicaNegocio:
    def __init__(self, db, kafka_handler):
        self.db = db
        self.kafka = kafka_handler
        self.suministros_activos = {}  # {cp_id: {'conductor_id': ..., 'suministro_id': ...}}

    def autenticar_cp(self, cp_id: str, ubicacion: str) -> bool:
        """
        Autentica un CP cuando se conecta
        - Verifica si existe en BD
        - Actualiza su estado a 'activado'
        """
        cp = self.db.obtener_cp(cp_id)

        if cp is None:
            # CP no existe, registrarlo
            print(f"📝 Registrando nuevo CP: {cp_id}")
            self.db.registrar_cp(cp_id, ubicacion)

        # Actualizar estado a activado
        self.db.actualizar_estado_cp(cp_id, 'activado')
        print(f"✓ CP {cp_id} autenticado y activado")
        return True

    def procesar_solicitud_suministro(self, mensaje: dict):
        """
        Procesa una solicitud de suministro de un conductor
        Mensaje esperado: {'conductor_id': 'DRV001', 'cp_id': 'CP001'}
        """
        conductor_id = mensaje.get('conductor_id')
        cp_id = mensaje.get('cp_id')

        print(f"\n📋 Procesando solicitud: Conductor {conductor_id} → CP {cp_id}")

        # 1. Verificar que el conductor existe
        conductor = self.db.obtener_conductor(conductor_id)
        if not conductor:
            print(f"✗ Conductor {conductor_id} no existe")
            self._enviar_respuesta_conductor(conductor_id, cp_id, False, "Conductor no registrado")
            return

        # 2. Verificar que el CP existe
        cp = self.db.obtener_cp(cp_id)
        if not cp:
            print(f"✗ CP {cp_id} no existe")
            self._enviar_respuesta_conductor(conductor_id, cp_id, False, "CP no encontrado")
            return

        # 3. Verificar que el CP está disponible
        if cp['estado'] != 'activado':
            print(f"✗ CP {cp_id} no está disponible (estado: {cp['estado']})")
            self._enviar_respuesta_conductor(conductor_id, cp_id, False, f"CP no disponible: {cp['estado']}")
            return

        # 4. Todo OK - Crear suministro y autorizar
        suministro_id = self.db.crear_suministro(conductor_id, cp_id)
        self.db.actualizar_estado_cp(cp_id, 'suministrando')

        # Guardar info del suministro activo
        self.suministros_activos[cp_id] = {
            'conductor_id': conductor_id,
            'suministro_id': suministro_id,
            'consumo_actual': 0.0,
            'importe_actual': 0.0
        }

        print(f"✓ Suministro autorizado (ID: {suministro_id})")

        # 5. Notificar al conductor
        self._enviar_respuesta_conductor(conductor_id, cp_id, True, "Suministro autorizado")

        # 6. Notificar al CP para que inicie el suministro
        self.kafka.enviar_mensaje('comandos_cp', {
            'tipo': 'INICIAR_SUMINISTRO',
            'cp_id': cp_id,
            'conductor_id': conductor_id,
            'suministro_id': suministro_id
        })

    def _enviar_respuesta_conductor(self, conductor_id: str, cp_id: str, autorizado: bool, mensaje: str):
        """Envía respuesta al conductor vía Kafka"""
        self.kafka.enviar_mensaje('respuestas_conductor', {
            'conductor_id': conductor_id,
            'cp_id': cp_id,
            'autorizado': autorizado,
            'mensaje': mensaje
        })

    def procesar_telemetria_cp(self, mensaje: dict):
        """
        Procesa telemetría en tiempo real de un CP durante un suministro
        Mensaje: {'cp_id': 'CP001', 'conductor_id': 'DRV001', 'consumo_actual': 5.2, 'importe_actual': 1.82}
        """
        cp_id = mensaje.get('cp_id')
        conductor_id = mensaje.get('conductor_id')
        consumo_actual = mensaje.get('consumo_actual', 0.0)
        importe_actual = mensaje.get('importe_actual', 0.0)

        if cp_id in self.suministros_activos:
            # Actualizar valores en memoria
            self.suministros_activos[cp_id]['consumo_actual'] = consumo_actual
            self.suministros_activos[cp_id]['importe_actual'] = importe_actual

            # Actualizar en BD
            suministro_id = self.suministros_activos[cp_id]['suministro_id']
            self.db.actualizar_suministro(suministro_id, consumo_actual, importe_actual)

            # La telemetría ya está en el topic correcto (telemetria_cp)
            # El driver debe suscribirse a 'telemetria_cp' no 'telemtria_cp'

    def procesar_fin_suministro(self, mensaje: dict):
        """
        Procesa la finalización de un suministro
        Mensaje: {'cp_id': 'CP001', 'consumo_kwh': 10.5, 'importe': 3.68}
        """
        cp_id = mensaje.get('cp_id')
        consumo_kwh = mensaje.get('consumo_kwh', 0.0)
        importe = mensaje.get('importe', 0.0)

        print(f"\n🏁 Finalizando suministro en {cp_id}")

        if cp_id in self.suministros_activos:
            suministro_id = self.suministros_activos[cp_id]['suministro_id']
            conductor_id = self.suministros_activos[cp_id]['conductor_id']

            # Finalizar en BD
            self.db.finalizar_suministro(suministro_id, consumo_kwh, importe)

            # Cambiar estado CP a activado
            self.db.actualizar_estado_cp(cp_id, 'activado')

            # Enviar ticket al conductor
            self.kafka.enviar_mensaje('tickets', {
                'conductor_id': conductor_id,
                'cp_id': cp_id,
                'suministro_id': suministro_id,
                'consumo_kwh': consumo_kwh,
                'importe_total': importe
            })

            # Eliminar de suministros activos
            del self.suministros_activos[cp_id]

            print(f"✓ Suministro finalizado. Ticket enviado a {conductor_id}")

    def procesar_averia_cp(self, mensaje: dict):
        """
        Procesa notificación de avería de un CP
        Mensaje: {'cp_id': 'CP001', 'descripcion': 'Fallo en sensor'}
        """
        cp_id = mensaje.get('cp_id')
        descripcion = mensaje.get('descripcion', 'Avería desconocida')

        print(f"\n⚠️ AVERÍA en {cp_id}: {descripcion}")

        # Actualizar estado en BD
        self.db.actualizar_estado_cp(cp_id, 'averiado')

        # Si estaba suministrando, finalizar suministro de emergencia
        if cp_id in self.suministros_activos:
            info = self.suministros_activos[cp_id]
            self.db.finalizar_suministro(
                info['suministro_id'],
                info['consumo_actual'],
                info['importe_actual']
            )

            # Notificar al conductor
            self.kafka.enviar_mensaje('notificaciones', {
                'tipo': 'AVERIA_DURANTE_SUMINISTRO',
                'conductor_id': info['conductor_id'],
                'cp_id': cp_id,
                'mensaje': 'Suministro interrumpido por avería'
            })

            del self.suministros_activos[cp_id]

    def procesar_recuperacion_cp(self, mensaje: dict):
        """
        Procesa notificación de recuperación de un CP tras avería
        Mensaje: {'cp_id': 'CP001'}
        """
        cp_id = mensaje.get('cp_id')
        print(f"\n✓ CP {cp_id} recuperado de avería")

        # Volver a estado activado
        self.db.actualizar_estado_cp(cp_id, 'activado')

    def parar_cp(self, cp_id: str):
        """Envía comando para parar un CP manualmente"""
        print(f"🛑 Parando CP {cp_id}")

        self.kafka.enviar_mensaje('comandos_cp', {
            'tipo': 'PARAR',
            'cp_id': cp_id
        })

        self.db.actualizar_estado_cp(cp_id, 'parado')

    def reanudar_cp(self, cp_id: str):
        """Envía comando para reanudar un CP"""
        print(f"▶️ Reanudando CP {cp_id}")

        self.kafka.enviar_mensaje('comandos_cp', {
            'tipo': 'REANUDAR',
            'cp_id': cp_id
        })

        self.db.actualizar_estado_cp(cp_id, 'activado')

    def obtener_estado_sistema(self):
        """Retorna el estado actual de todos los CPs y suministros"""
        return {
            'cps': self.db.obtener_todos_los_cps(),
            'suministros_activos': self.suministros_activos
        }
