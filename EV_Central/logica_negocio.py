"""
Lógica de negocio para EV_Central
Contiene las reglas y validaciones del sistema
"""


class LogicaNegocio:
    def __init__(self, db, kafka_handler):
        self.db = db
        self.kafka = kafka_handler
        self.suministros_activos = {}  # {cp_id: {'conductor_id': ..., 'suministro_id': ...}}

        # Recuperar estado tras reinicio
        self.recuperar_estado_sistema()

    def autenticar_cp(self, cp_id: str) -> bool:
        """
        Autentica un CP cuando se conecta vía socket
        - Verifica si existe en BD
        - Si no existe, lo registra
        - Actualiza su estado a 'activado'
        """
        cp = self.db.obtener_cp(cp_id)

        if cp is None:
            # CP no existe, registrarlo
            print(f"Registrando nuevo CP: {cp_id}")
            self.db.registrar_cp(cp_id)

        # Actualizar estado a activado
        self.db.actualizar_estado_cp(cp_id, 'activado')
        print(f"[OK] CP {cp_id} autenticado y activado")
        return True

    def procesar_iniciar_cp(self, mensaje: dict):
        """
        Procesa la inicialización de un CP cuando arranca
        Mensaje: {'cp_id': 'CP001'}
        """
        cp_id = mensaje.get('cp_id')

        if not cp_id:
            print("[ERROR] Mensaje de iniciar_cp sin cp_id")
            return

        print(f"\n[INICIO] CP {cp_id} iniciando...")

        # Verificar si existe en BD, si no, registrarlo
        cp = self.db.obtener_cp(cp_id)
        if cp is None:
            print(f"Registrando nuevo CP: {cp_id}")
            self.db.registrar_cp(cp_id)

        # Actualizar estado a activado
        self.db.actualizar_estado_cp(cp_id, 'activado')
        print(f"[OK] CP {cp_id} activado")

    def procesar_solicitud_suministro(self, mensaje: dict):
        """
        Procesa una solicitud de suministro
        Puede venir de:
        1. Un conductor via App: {'conductor_id': 'DRV001', 'cp_id': 'CP001'}
        2. Un CP de forma manual: {'conductor_id': 'DRV001', 'cp_id': 'CP001', 'origen': 'CP'}
        """
        conductor_id = mensaje.get('conductor_id')
        cp_id = mensaje.get('cp_id')
        origen = mensaje.get('origen', 'CONDUCTOR')  # Por defecto asume que viene del conductor

        print(f"\nProcesando solicitud [{origen}]: Conductor {conductor_id} -> CP {cp_id}")

        # 1. Verificar que el conductor existe (si no, auto-registrar)
        conductor = self.db.obtener_conductor(conductor_id)
        if not conductor:
            print(f"Auto-registrando conductor {conductor_id}")
            self.db.registrar_conductor(conductor_id)

        # 2. Verificar que el CP existe
        cp = self.db.obtener_cp(cp_id)
        if not cp:
            print(f"[ERROR] CP {cp_id} no existe")
            self._enviar_respuesta_solicitud(conductor_id, cp_id, False, "CP no encontrado", origen)
            return

        # 3. Verificar que el CP esta disponible
        if cp['estado'] != 'activado':
            print(f"[ERROR] CP {cp_id} no esta disponible (estado: {cp['estado']})")
            self._enviar_respuesta_solicitud(conductor_id, cp_id, False, f"CP no disponible: {cp['estado']}", origen)
            return

        # 4. Todo OK - Crear suministro y autorizar
        suministro_id = self.db.crear_suministro(conductor_id, cp_id)
        self.db.actualizar_estado_cp(cp_id, 'suministrando')

        # Guardar info del suministro activo en memoria
        self.suministros_activos[cp_id] = {
            'conductor_id': conductor_id,
            'suministro_id': suministro_id,
            'consumo_actual': 0.0,
            'importe_actual': 0.0
        }

        print(f"[OK] Suministro autorizado (ID: {suministro_id})")

        # 5. Notificar según el origen
        self._enviar_respuesta_solicitud(conductor_id, cp_id, True, "Suministro autorizado", origen)

        # 6. Notificar al CP para que inicie el suministro
        self.kafka.enviar_mensaje('comandos_cp', {
            'tipo': 'INICIAR_SUMINISTRO',
            'cp_id': cp_id,
            'conductor_id': conductor_id,
            'suministro_id': suministro_id
        })

    def _enviar_respuesta_solicitud(self, conductor_id: str, cp_id: str, autorizado: bool, mensaje: str, origen: str):
        """
        Envía respuesta según el origen de la solicitud
        - Si viene del CONDUCTOR: envía a 'respuestas_conductor'
        - Si viene del CP: envía a 'respuestas_cp' (para que el CP informe al usuario)
        """
        if origen == 'CP':
            # Responder al CP para que muestre el resultado en su interfaz
            self.kafka.enviar_mensaje('respuestas_cp', {
                'cp_id': cp_id,
                'conductor_id': conductor_id,
                'autorizado': autorizado,
                'mensaje': mensaje
            })
        else:
            # Responder al conductor (aplicación móvil/driver)
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

        print(f"\n[FIN] Finalizando suministro en {cp_id}")

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

            print(f"[OK] Suministro finalizado. Ticket enviado a {conductor_id}")

    def procesar_averia_cp(self, mensaje: dict):
        """
        Procesa notificación de avería de un CP
        Mensaje: {'cp_id': 'CP001', 'descripcion': 'Fallo en sensor'}
        """
        cp_id = mensaje.get('cp_id')
        descripcion = mensaje.get('descripcion', 'Averia desconocida')

        print(f"\n[AVISO] AVERIA en {cp_id}: {descripcion}")

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
        print(f"\n[OK] CP {cp_id} recuperado de averia")

        # Volver a estado activado
        self.db.actualizar_estado_cp(cp_id, 'activado')

    def procesar_estado_engine(self, cp_id: str, estado_engine: str):
        """
        Procesa el estado del Engine reportado por el Monitor via socket.
        Monitor_OK + Engine_OK => activado (verde)
        Monitor_OK + Engine_KO => averiado (rojo)
        """
        cp = self.db.obtener_cp(cp_id)
        if not cp:
            return

        estado_actual = cp['estado']

        # Si el CP está parado manualmente desde la GUI, ignorar todos los reportes del Engine
        if estado_actual == 'parado':
            return

        if estado_engine == 'OK':
            # Engine OK -> CP disponible
            if estado_actual in ['averiado', 'desconectado']:
                print(f"[ENGINE OK] CP {cp_id} -> activado")
                self.db.actualizar_estado_cp(cp_id, 'activado')

        elif estado_engine in ['KO', 'AVERIA']:
            # Engine KO -> CP averiado
            print(f"[ENGINE KO] CP {cp_id} -> averiado")
            self.db.actualizar_estado_cp(cp_id, 'averiado')

            # Si estaba suministrando, finalizar de emergencia
            if cp_id in self.suministros_activos:
                info = self.suministros_activos[cp_id]
                print(f"[EMERGENCIA] Finalizando suministro en {cp_id} por avería del Engine")

                self.db.finalizar_suministro(
                    info['suministro_id'],
                    info['consumo_actual'],
                    info['importe_actual']
                )

                self.kafka.enviar_mensaje('notificaciones', {
                    'tipo': 'AVERIA_ENGINE',
                    'conductor_id': info['conductor_id'],
                    'cp_id': cp_id,
                    'mensaje': f'Suministro interrumpido: Engine de CP {cp_id} averiado'
                })

                del self.suministros_activos[cp_id]

    def manejar_desconexion_monitor(self, cp_id: str):
        """
        Llamado desde servidor_socket cuando un Monitor se desconecta.
        Marca el CP como desconectado y finaliza suministros si los hay.
        Monitor_KO => desconectado (gris)
        """
        print(f"\n[DESCONEXIÓN] Monitor de CP {cp_id} desconectado")

        # Actualizar estado a desconectado
        self.db.actualizar_estado_cp(cp_id, 'desconectado')

        # Si estaba suministrando, finalizar de emergencia
        if cp_id in self.suministros_activos:
            info = self.suministros_activos[cp_id]

            print(f"[EMERGENCIA] Finalizando suministro en {cp_id} por desconexión del Monitor")

            self.db.finalizar_suministro(
                info['suministro_id'],
                info['consumo_actual'],
                info['importe_actual']
            )

            # Notificar al conductor
            self.kafka.enviar_mensaje('notificaciones', {
                'tipo': 'CP_DESCONECTADO',
                'conductor_id': info['conductor_id'],
                'cp_id': cp_id,
                'mensaje': f'Suministro interrumpido: CP {cp_id} desconectado'
            })

            del self.suministros_activos[cp_id]

    def parar_cp(self, cp_id: str):
        """Envia comando para parar un CP manualmente"""
        print(f"[STOP] Parando CP {cp_id}")

        self.kafka.enviar_mensaje('comandos_cp', {
            'tipo': 'PARAR',
            'cp_id': cp_id
        })

        self.db.actualizar_estado_cp(cp_id, 'parado')

    def reanudar_cp(self, cp_id: str):
        """Envia comando para reanudar un CP"""
        print(f"[PLAY] Reanudando CP {cp_id}")

        self.kafka.enviar_mensaje('comandos_cp', {
            'tipo': 'REANUDAR',
            'cp_id': cp_id
        })

        self.db.actualizar_estado_cp(cp_id, 'activado')

    def parar_todos_cps(self):
        """Para TODOS los CPs que estén activos o suministrando"""
        cps = self.db.obtener_todos_los_cps()

        for cp in cps:
            if cp['estado'] in ['activado', 'suministrando']:
                self.parar_cp(cp['id'])

        print(f"[STOP ALL] Comando de parada enviado a todos los CPs activos")

    def reanudar_todos_cps(self):
        """Reanuda TODOS los CPs que estén parados"""
        cps = self.db.obtener_todos_los_cps()

        for cp in cps:
            if cp['estado'] == 'parado':
                self.reanudar_cp(cp['id'])

        print(f"[PLAY ALL] Comando de reanudación enviado a todos los CPs parados")

    def obtener_estado_sistema(self):
        """Retorna el estado actual de todos los CPs y suministros"""
        return {
            'cps': self.db.obtener_todos_los_cps(),
            'suministros_activos': self.suministros_activos
        }

    def recuperar_estado_sistema(self):
        """
        Recupera el estado del sistema desde la BBDD tras un reinicio de la Central.
        Esto es CRÍTICO para poder enviar tickets pendientes si la Central se cayó.
        """
        print("\nRecuperando estado del sistema desde BBDD...")

        # Recuperar suministros que estaban en curso cuando se cayo el sistema
        try:
            suministros_pendientes = self.db.obtener_suministros_activos()

            if suministros_pendientes:
                print(f"Se encontraron {len(suministros_pendientes)} suministros activos en BBDD")

                for suministro in suministros_pendientes:
                    cp_id = suministro['cp_id']
                    conductor_id = suministro['conductor_id']
                    suministro_id = suministro['id']

                    # Restaurar en memoria
                    self.suministros_activos[cp_id] = {
                        'conductor_id': conductor_id,
                        'suministro_id': suministro_id,
                        'consumo_actual': float(suministro.get('consumo_kwh', 0.0)),
                        'importe_actual': float(suministro.get('importe_total', 0.0))
                    }

                    print(f"  [OK] Recuperado: CP {cp_id} - Conductor {conductor_id} (ID: {suministro_id})")
            else:
                print("[OK] No hay suministros activos pendientes")

        except Exception as e:
            print(f"[AVISO] Error recuperando estado: {e}")
            # No es crítico, el sistema puede continuar
