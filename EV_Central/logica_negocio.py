"""
Lógica de negocio para EV_Central
Contiene las reglas y validaciones del sistema
"""


class LogicaNegocio:
    def __init__(self, db, kafka_handler, servidor_socket=None):
        self.db = db
        self.kafka = kafka_handler
        self.servidor_socket = servidor_socket  # Referencia al servidor socket para enviar comandos
        self.suministros_activos = {}  # {cp_id: {'conductor_id': ..., 'suministro_id': ...}}

        # NO recuperar suministros aquí - se recuperarán cuando los CPs se reconecten

    def autenticar_cp(self, cp_id: str) -> bool:
        """
        Autentica un CP (Monitor) cuando se conecta vía socket
        - Verifica si existe en BD
        - Si no existe, lo registra
        - Recupera suministro activo si existe (para recuperación tras caída)
        - NO actualiza el estado aún (esperará a que el Monitor reporte el estado del Engine)
        """
        print(f"[AUTENTICACIÓN] CP {cp_id} conectándose...")

        try:
            cp = self.db.obtener_cp(cp_id)

            if not cp:
                # CP no existe, registrarlo con estado 'desconectado'
                print(f"[REGISTRO] Nuevo CP: {cp_id}")
                self.db.registrar_cp(cp_id)
            else:
                print(f"[RECONEXIÓN] CP {cp_id} reconectándose (estado: {cp.get('estado', 'desconocido')})")

            # NO recuperar suministros aquí - se recuperarán cuando el Engine reporte SUMINISTRANDO
            # Esto evita mostrar suministros antiguos que ya no están activos

            print(f"[OK] Monitor de CP {cp_id} autenticado")
            return True

        except Exception as e:
            print(f"[ERROR] Error autenticando CP {cp_id}: {e}")
            return False

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
        # Para Izan, añadi que tambien mande el id del suministro
        self._enviar_respuesta_solicitud(conductor_id, cp_id, True, "Suministro autorizado", origen, suministro_id)

        # 6. Notificar al CP para que inicie el suministro
        self.kafka.enviar_mensaje('comandos_cp', {
            'tipo': 'INICIAR_SUMINISTRO',
            'cp_id': cp_id,
            'conductor_id': conductor_id,
            'suministro_id': suministro_id
        })
                                                                                                                      #cambio
    def _enviar_respuesta_solicitud(self, conductor_id: str, cp_id: str, autorizado: bool, mensaje: str, origen: str, suministro_id: int):
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
                'mensaje': mensaje,
                'suministro_id': suministro_id # Añadido
            })
        else:
            # Responder al conductor (aplicación móvil/driver)
            self.kafka.enviar_mensaje('respuestas_conductor', {
                'conductor_id': conductor_id,
                'cp_id': cp_id,
                'autorizado': autorizado,
                'mensaje': mensaje,
                'suministro_id': suministro_id # Añadido
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
        Mensaje del Engine: {'conductor_id': 'DRV001', 'cp_id': 'CP001', 'suministro_id': 123,
                             'consumo_kwh': 10.5, 'importe_total': 3.68}
        """
        cp_id = mensaje.get('cp_id')
        conductor_id = mensaje.get('conductor_id')
        suministro_id = mensaje.get('suministro_id')
        consumo_kwh = mensaje.get('consumo_kwh', 0.0)
        importe = mensaje.get('importe_total', 0.0)  # El Engine envía 'importe_total', no 'importe'

        print(f"\n[FIN] Finalizando suministro en {cp_id}")

        if cp_id in self.suministros_activos:
            # Usar el suministro_id que viene del Engine (más confiable)
            info = self.suministros_activos[cp_id]
            suministro_id_memoria = info['suministro_id']
            conductor_id_memoria = info['conductor_id']

            # Verificar consistencia (opcional, para debug)
            if suministro_id and suministro_id != suministro_id_memoria:
                print(f"[AVISO] Suministro ID inconsistente: Engine={suministro_id}, Memoria={suministro_id_memoria}")

            # Usar el suministro_id de memoria (más confiable)
            final_suministro_id = suministro_id_memoria
            final_conductor_id = conductor_id_memoria

            # Finalizar en BD
            self.db.finalizar_suministro(final_suministro_id, consumo_kwh, importe)

            # Enviar ticket al conductor
            self.kafka.enviar_mensaje('tickets', {
                'conductor_id': final_conductor_id,
                'cp_id': cp_id,
                'suministro_id': final_suministro_id,
                'consumo_kwh': consumo_kwh,
                'importe_total': importe
            })

            # Eliminar de suministros activos
            del self.suministros_activos[cp_id]

            print(f"[OK] Suministro finalizado. Ticket enviado a {final_conductor_id}")
            print(f"[ESPERA] CP {cp_id} esperará 4 segundos antes de estar disponible de nuevo...")

            # Iniciar hilo para esperar 4 segundos antes de activar el CP
            import threading
            def activar_tras_espera():
                import time
                time.sleep(4)
                # Verificar que el CP no ha cambiado de estado (avería, parado, etc.)
                cp_actual = self.db.obtener_cp(cp_id)
                if cp_actual and cp_actual['estado'] == 'suministrando':
                    self.db.actualizar_estado_cp(cp_id, 'activado')
                    print(f"[OK] CP {cp_id} disponible de nuevo tras período de espera")

            threading.Thread(target=activar_tras_espera, daemon=True).start()
        else:
            print(f"[AVISO] Fin de suministro recibido para {cp_id} pero no hay suministro activo en memoria")
            # Intentar finalizar de todos modos si tenemos los datos
            if suministro_id and conductor_id:
                self.db.finalizar_suministro(suministro_id, consumo_kwh, importe)

                # Enviar ticket
                self.kafka.enviar_mensaje('tickets', {
                    'conductor_id': conductor_id,
                    'cp_id': cp_id,
                    'suministro_id': suministro_id,
                    'consumo_kwh': consumo_kwh,
                    'importe_total': importe
                })
                print(f"[OK] Suministro {suministro_id} finalizado (recuperado). Ticket enviado a {conductor_id}")
                print(f"[ESPERA] CP {cp_id} esperará 4 segundos antes de estar disponible de nuevo...")

                # Iniciar hilo para esperar 4 segundos antes de activar el CP
                import threading
                def activar_tras_espera():
                    import time
                    time.sleep(4)
                    cp_actual = self.db.obtener_cp(cp_id)
                    if cp_actual and cp_actual['estado'] == 'suministrando':
                        self.db.actualizar_estado_cp(cp_id, 'activado')
                        print(f"[OK] CP {cp_id} disponible de nuevo tras período de espera")

                threading.Thread(target=activar_tras_espera, daemon=True).start()

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
        Estados posibles del Engine:
        - 'OK' -> CP disponible (activado - verde)
        - 'AVERIA' -> CP averiado (rojo)
        - 'PARADO' -> CP parado manualmente desde el Engine

        Monitor_OK + Engine_OK => activado (verde)
        Monitor_OK + Engine_AVERIA => averiado (rojo)
        Monitor desconectado => desconectado (gris)
        """
        print(f"[DEBUG] Recibido estado '{estado_engine}' para CP {cp_id}")

        cp = self.db.obtener_cp(cp_id)
        if not cp:
            print(f"[ERROR] CP {cp_id} no encontrado en BD al procesar estado")
            return

        estado_actual = cp['estado']
        print(f"[DEBUG] Estado actual del CP {cp_id} en BD: {estado_actual}")

        # Si el CP está parado manualmente desde la GUI, ignorar todos los reportes del Engine
        if estado_actual == 'parado':
            print(f"[INFO] CP {cp_id} parado manualmente, ignorando estado del Engine")
            return

        if estado_engine == 'OK':
            # Engine OK -> CP disponible
            # Solo cambiar a activado si no está suministrando actualmente
            if estado_actual != 'suministrando':
                print(f"[ESTADO] CP {cp_id} -> activado (Engine OK)")
                resultado = self.db.actualizar_estado_cp(cp_id, 'activado')
                print(f"[DEBUG] Actualización BD resultado: {resultado}")

        elif estado_engine == 'SUMINISTRANDO':
            # Engine reporta que está suministrando
            if estado_actual != 'suministrando':
                print(f"[ESTADO] CP {cp_id} -> suministrando (Engine reporta SUMINISTRANDO)")
                self.db.actualizar_estado_cp(cp_id, 'suministrando')

            # Recuperar suministro de BD si no está en memoria (recuperación tras caída de Central)
            if cp_id not in self.suministros_activos:
                suministro = self.db.obtener_suministro_activo(cp_id)
                if suministro:
                    print(f"[RECUPERACIÓN] Suministro activo encontrado para {cp_id}")
                    self.suministros_activos[cp_id] = {
                        'conductor_id': suministro['conductor_id'],
                        'suministro_id': suministro['id'],
                        'consumo_actual': float(suministro.get('consumo_kwh', 0.0)),
                        'importe_actual': float(suministro.get('importe_total', 0.0))
                    }
                    print(f"  [OK] Recuperado suministro ID {suministro['id']} - Conductor {suministro['conductor_id']}")
                else:
                    print(f"[AVISO] Engine reporta SUMINISTRANDO pero no hay suministro activo en BD para {cp_id}")

        elif estado_engine == 'PARADO':
            # Monitor reporta que está parado manualmente
            print(f"[ESTADO] CP {cp_id} -> parado (Monitor reporta PARADO)")
            self.db.actualizar_estado_cp(cp_id, 'parado')

        elif estado_engine == 'AVERIA':
            # Engine AVERIA -> CP averiado
            print(f"[AVERIA] CP {cp_id} -> averiado (Engine reporta AVERIA)")
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
        """Para un CP manualmente desde la GUI"""
        print(f"[STOP] Parando CP {cp_id}")

        # Actualizar estado en BD
        resultado = self.db.actualizar_estado_cp(cp_id, 'parado')
        print(f"[DEBUG] Estado 'parado' actualizado en BD: {resultado}")

        # Enviar comando PARAR al Monitor por socket
        if self.servidor_socket:
            comando = {'tipo': 'PARAR', 'cp_id': cp_id}
            enviado = self.servidor_socket.enviar_a_cp(cp_id, comando)
            if enviado:
                print(f"[OK] Comando PARAR enviado al Monitor de {cp_id}")
            else:
                print(f"[ERROR] No se pudo enviar comando PARAR al Monitor de {cp_id}")
        else:
            print(f"[ERROR] Servidor socket no disponible para enviar comando")

    def reanudar_cp(self, cp_id: str):
        """Reanuda un CP que estaba parado manualmente"""
        print(f"[PLAY] Reanudando CP {cp_id}")

        # Actualizar estado en BD temporalmente
        # El Monitor enviará el estado real del Engine en el próximo ciclo
        resultado = self.db.actualizar_estado_cp(cp_id, 'desconectado')
        print(f"[DEBUG] Estado actualizado en BD: {resultado}")

        # Enviar comando REANUDAR al Monitor por socket
        if self.servidor_socket:
            comando = {'tipo': 'REANUDAR', 'cp_id': cp_id}
            enviado = self.servidor_socket.enviar_a_cp(cp_id, comando)
            if enviado:
                print(f"[OK] Comando REANUDAR enviado al Monitor de {cp_id}")
                # El Monitor enviará el estado real (OK/AVERIA) en ~1 segundo
            else:
                print(f"[ERROR] No se pudo enviar comando REANUDAR al Monitor de {cp_id}")
        else:
            print(f"[ERROR] Servidor socket no disponible para enviar comando")

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

