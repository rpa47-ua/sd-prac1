"""
Lógica de negocio para EV_Central
Contiene las reglas y validaciones del sistema
"""
import time
import threading
from database import Database
from kafka_handler import KafkaHandler

class LogicaNegocio:
    def __init__(self, db, kafka_handler, servidor_socket=None):
        self.db = db
        self.kafka = kafka_handler
        self.servidor_socket = servidor_socket
        self.suministros_activos = {}
        self.colas_espera = {}
        self.running = True

    def recuperar_suministros_al_inicio(self):
        """Recupera suministros activos y envía tickets pendientes al reiniciar Central"""
        print("\n[RECUPERACIÓN] Solicitando estado de suministros a todos los Engines...")

        # 1. Solicitar a todos los Engines que reporten su estado actual
        self.kafka.enviar_mensaje('solicitud_estado_engine', {
            'tipo': 'SOLICITAR_ESTADO',
            'timestamp': time.time()
        })
        time.sleep(2)

        # 2. Enviar tickets pendientes (suministros finalizados sin ticket)
        print("\n[RECUPERACIÓN] Buscando tickets pendientes en la BD...")
        tickets_pendientes = self.db.obtener_suministros_pendientes_ticket()
        for suministro in tickets_pendientes:
            conductor_id = suministro['conductor_id']
            cp_id = suministro['cp_id']
            suministro_id = suministro['id']
            consumo_kwh = suministro['consumo_kwh']
            importe_total = suministro['importe_total']

            # Enviar ticket
            self.kafka.enviar_mensaje('tickets', {
                'conductor_id': conductor_id,
                'cp_id': cp_id,
                'suministro_id': suministro_id,
                'consumo_kwh': consumo_kwh,
                'importe_total': importe_total
            })
            time.sleep(2)

            # Marcar como enviado
            self.db.marcar_ticket_enviado(suministro_id)
            print(f"[TICKET ENVIADO] Suministro {suministro_id} - Conductor {conductor_id}")

        if tickets_pendientes:
            print(f"\n[OK] {len(tickets_pendientes)} tickets pendientes enviados")
        else:
            print("\n[OK] No hay tickets pendientes")

        print("[INFO] Esperando respuestas de los Engines...\n")

    def _publicar_estado_cp(self, cp_id: str, estado: str):
        try:
            self.kafka.enviar_mensaje('estado_cps', {
                'tipo': 'ESTADO_CP',
                'cp_id': cp_id,
                'estado': estado
            })
        except Exception:
            print("[ERROR] No se puede publicar el estado")
        
    
    def procesar_solicitud_listado(self, mensaje: dict):
        try:
            tipo = mensaje.get('tipo')
            
            if tipo == 'SOLICITUD':
                print(f"[SOLICITUD] Recibida solicitud de estados de todos los CPs")
                self._publicar_estados_completos()
                
        except Exception:
            print(f"[ERROR] Procesando solicitud de listado")

    def _publicar_estados_completos(self):
        try:
            cps = self.db.obtener_todos_los_cps()
            print(f"[PUBLICACIÓN] Enviando estados completos de {len(cps)} CPs")
            
            for cp in cps:
                self._publicar_estado_cp(cp['id'], cp['estado'])
                time.sleep(0.05)
                
            print(f"[OK] Estados completos de todos los CPs publicados")
            
        except Exception:
            print(f"[ERROR] Publicando estados completos")
        
    

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
        origen = mensaje.get('origen', 'CONDUCTOR')

        print(f"\nProcesando solicitud [{origen}]: Conductor {conductor_id} -> CP {cp_id}")

        # 1. Verificar que el conductor existe y está conectado
        conductor = self.db.obtener_conductor(conductor_id)
        if not conductor:
            print(f"[ERROR] Conductor {conductor_id} no registrado en el sistema")
            self._enviar_respuesta_solicitud(conductor_id, cp_id, False, "Conductor no registrado", origen, None)
            return

        if not conductor.get('conectado', False):
            print(f"[ERROR] Conductor {conductor_id} no está conectado")
            self._enviar_respuesta_solicitud(conductor_id, cp_id, False, "Conductor no conectado", origen, None)
            return

        # 2. Verificar que el CP existe
        cp = self.db.obtener_cp(cp_id)
        if not cp:
            print(f"[ERROR] CP {cp_id} no existe")
            self._enviar_respuesta_solicitud(conductor_id, cp_id, False, "CP no encontrado", origen, None)
            return

        # 3. Verificar que el CP esta disponible
        if cp['estado'] != 'activado':
            print(f"[INFO] CP {cp_id} no esta disponible (estado: {cp['estado']})")

            # Solo poner en cola si está suministrando (ocupado)
            if cp['estado'] == 'suministrando':
                if cp_id not in self.colas_espera:
                    self.colas_espera[cp_id] = []

                self.colas_espera[cp_id].append({
                    'conductor_id': conductor_id,
                    'origen': origen
                })

                posicion = len(self.colas_espera[cp_id])
                print(f"[COLA] Conductor {conductor_id} añadido a la cola de {cp_id} (posición {posicion})")
                self._enviar_respuesta_solicitud(conductor_id, cp_id, False, f"CP ocupado. En cola, posición {posicion}", origen, None)
            else:
                # Rechazar directamente si está desconectado, averiado o parado
                print(f"[RECHAZO] Solicitud rechazada para {cp_id} (estado: {cp['estado']})")
                self._enviar_respuesta_solicitud(conductor_id, cp_id, False, f"CP no disponible: {cp['estado']}", origen, None)
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
        self._enviar_respuesta_solicitud(conductor_id, cp_id, True, "Suministro autorizado", origen, suministro_id)

        # 6. Notificar al CP para que inicie el suministro
        self.kafka.enviar_mensaje('comandos_cp', {
            'tipo': 'INICIAR_SUMINISTRO',
            'cp_id': cp_id,
            'conductor_id': conductor_id,
            'suministro_id': suministro_id
        })
        time.sleep(2)
                                                                                                                      #cambio
    def _enviar_respuesta_solicitud(self, conductor_id: str, cp_id: str, autorizado: bool, mensaje: str, origen: str, suministro_id: int):
        """
        Envía respuesta según el origen de la solicitud
        - Si viene del CONDUCTOR: envía a 'respuestas_conductor'
        - Si viene del CP: envía a 'respuestas_cp' (para que el CP informe al usuario)
        """
        if origen == 'CP':
            self.kafka.enviar_mensaje('respuestas_cp', {
                'cp_id': cp_id,
                'conductor_id': conductor_id,
                'autorizado': autorizado,
                'mensaje': mensaje,
                'suministro_id': suministro_id
            })
            time.sleep(2)
        else:
            self.kafka.enviar_mensaje('respuestas_conductor', {
                'conductor_id': conductor_id,
                'cp_id': cp_id,
                'autorizado': autorizado,
                'mensaje': mensaje,
                'suministro_id': suministro_id
            })
            time.sleep(2)

    def _procesar_siguiente_en_cola(self, cp_id: str):
        """
        Procesa la siguiente solicitud en cola para un CP que se ha liberado
        """
        if cp_id not in self.colas_espera or len(self.colas_espera[cp_id]) == 0:
            print(f"[COLA] No hay solicitudes en espera para {cp_id}")
            return

        siguiente = self.colas_espera[cp_id].pop(0)
        conductor_id = siguiente['conductor_id']
        origen = siguiente['origen']

        print(f"[COLA] Procesando siguiente en cola: Conductor {conductor_id} -> CP {cp_id}")

        cp = self.db.obtener_cp(cp_id)
        if not cp or cp['estado'] != 'activado':
            print(f"[ERROR] CP {cp_id} no disponible para procesar cola")
            self.colas_espera[cp_id].insert(0, siguiente)
            return

        suministro_id = self.db.crear_suministro(conductor_id, cp_id)
        self.db.actualizar_estado_cp(cp_id, 'suministrando')

        self.suministros_activos[cp_id] = {
            'conductor_id': conductor_id,
            'suministro_id': suministro_id,
            'consumo_actual': 0.0,
            'importe_actual': 0.0
        }

        print(f"[OK] Suministro autorizado desde cola (ID: {suministro_id})")

        self._enviar_respuesta_solicitud(conductor_id, cp_id, True, "Suministro autorizado (desde cola)", origen, suministro_id)

        self.kafka.enviar_mensaje('comandos_cp', {
            'tipo': 'INICIAR_SUMINISTRO',
            'cp_id': cp_id,
            'conductor_id': conductor_id,
            'suministro_id': suministro_id
        })
        time.sleep(2)

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
        else:
            # Si no está en memoria, recuperar de BD (Central reiniciado durante suministro)
            suministro = self.db.obtener_suministro_activo(cp_id)
            if suministro:
                print(f"[RECUPERACIÓN] Telemetría recibida para {cp_id} sin suministro en memoria, recuperando de BD...")
                self.suministros_activos[cp_id] = {
                    'conductor_id': suministro['conductor_id'],
                    'suministro_id': suministro['id'],
                    'consumo_actual': consumo_actual,
                    'importe_actual': importe_actual
                }
                # Actualizar en BD con valores de telemetría
                self.db.actualizar_suministro(suministro['id'], consumo_actual, importe_actual)
                print(f"  [OK] Recuperado suministro ID {suministro['id']} con telemetría actual")

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
            time.sleep(2)

            # Marcar ticket como enviado
            self.db.marcar_ticket_enviado(final_suministro_id)

            # Eliminar de suministros activos
            del self.suministros_activos[cp_id]

            print(f"[OK] Suministro finalizado. Ticket enviado a {final_conductor_id}")
            print(f"[ESPERA] CP {cp_id} esperará 4 segundos antes de estar disponible de nuevo...")

            # Iniciar hilo para esperar 4 segundos antes de activar el CP
            import threading
            def activar_tras_espera():
                time.sleep(4)
                cp_actual = self.db.obtener_cp(cp_id)
                if cp_actual and cp_actual['estado'] == 'suministrando':
                    self.db.actualizar_estado_cp(cp_id, 'activado')
                    print(f"[OK] CP {cp_id} disponible de nuevo tras período de espera")
                    self._procesar_siguiente_en_cola(cp_id)

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
                time.sleep(2)

                # Marcar ticket como enviado
                self.db.marcar_ticket_enviado(suministro_id)

                print(f"[OK] Suministro {suministro_id} finalizado (recuperado). Ticket enviado a {conductor_id}")
                print(f"[ESPERA] CP {cp_id} esperará 4 segundos antes de estar disponible de nuevo...")

                def activar_tras_espera():
                    time.sleep(4)
                    cp_actual = self.db.obtener_cp(cp_id)
                    if cp_actual and cp_actual['estado'] == 'suministrando':
                        self.db.actualizar_estado_cp(cp_id, 'activado')
                        print(f"[OK] CP {cp_id} disponible de nuevo tras período de espera")
                        self._procesar_siguiente_en_cola(cp_id)

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
            time.sleep(2)

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

    def procesar_registro_conductor(self, mensaje: dict):
        """
        Procesa registro/desregistro de conductores
        Mensaje: {'tipo': 'CONECTAR'/'DESCONECTAR'/'RECUPERAR_SUMINISTRO', 'conductor_id': 'DRV001'}
        """
        tipo = mensaje.get('tipo')
        conductor_id = mensaje.get('conductor_id')

        if tipo == 'CONECTAR':
            print(f"[REGISTRO] Conductor {conductor_id} conectado")
            self.db.registrar_conductor(conductor_id, conectado=True)
        elif tipo == 'DESCONECTAR':
            print(f"[DESREGISTRO] Conductor {conductor_id} desconectado")
            self.db.actualizar_estado_conductor(conductor_id, conectado=False)
        elif tipo == 'RECUPERAR_SUMINISTRO':
            print(f"[RECUPERACION] Buscando suministro activo para {conductor_id}")
            # Buscar suministro activo del conductor
            suministro = self.db.obtener_suministro_activo_conductor(conductor_id)
            if suministro:
                print(f"[RECUPERACION] Suministro activo encontrado (ID: {suministro['id']}, CP: {suministro['cp_id']})")
                # Enviar información del suministro al conductor
                self.kafka.enviar_mensaje('respuestas_conductor', {
                    'conductor_id': conductor_id,
                    'cp_id': suministro['cp_id'],
                    'autorizado': True,
                    'mensaje': 'Suministro activo recuperado',
                    'suministro_id': suministro['id']
                })
                time.sleep(2)
            else:
                print(f"[RECUPERACION] No hay suministro activo para {conductor_id}")

    def procesar_respuesta_estado_engine(self, mensaje: dict):
        """
        Procesa respuesta de Engine con estado de suministro
        Mensaje: {'cp_id': 'CP001', 'activo': True/False, 'conductor_id': 'DRV001',
                  'suministro_id': 123, 'consumo_actual': 5.2, 'importe_actual': 1.82}
        """
        cp_id = mensaje.get('cp_id')
        activo = mensaje.get('activo', False)

        if activo:
            # Suministro activo - recuperar a memoria
            conductor_id = mensaje.get('conductor_id')
            suministro_id = mensaje.get('suministro_id')
            consumo_actual = mensaje.get('consumo_actual', 0.0)
            importe_actual = mensaje.get('importe_actual', 0.0)

            print(f"[RECUPERACIÓN] Engine {cp_id} reporta suministro activo (ID: {suministro_id})")

            self.suministros_activos[cp_id] = {
                'conductor_id': conductor_id,
                'suministro_id': suministro_id,
                'consumo_actual': consumo_actual,
                'importe_actual': importe_actual
            }

            # Actualizar en BD
            self.db.actualizar_suministro(suministro_id, consumo_actual, importe_actual)
            print(f"  [OK] Suministro recuperado: {consumo_actual} kWh, {importe_actual} €")
        else:
            print(f"[INFO] Engine {cp_id} no tiene suministro activo")

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
            if estado_actual != 'suministrando':
                print(f"[ESTADO] CP {cp_id} -> activado (Engine OK)")
                resultado = self.db.actualizar_estado_cp(cp_id, 'activado')
                print(f"[DEBUG] Actualización BD resultado: {resultado}")
                self._publicar_estado_cp(cp_id, 'activado')

        elif estado_engine == 'SUMINISTRANDO':
            if estado_actual != 'suministrando':
                print(f"[ESTADO] CP {cp_id} -> suministrando (Engine reporta SUMINISTRANDO)")
                self.db.actualizar_estado_cp(cp_id, 'suministrando')
                self._publicar_estado_cp(cp_id, 'suministrando')

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
            print(f"[ESTADO] CP {cp_id} -> parado (Monitor reporta PARADO)")
            self.db.actualizar_estado_cp(cp_id, 'parado')
            self._publicar_estado_cp(cp_id, 'parado')

        elif estado_engine == 'AVERIA':
            print(f"[AVERIA] CP {cp_id} -> averiado (Engine reporta AVERIA)")
            self.db.actualizar_estado_cp(cp_id, 'averiado')
            self._publicar_estado_cp(cp_id, 'averiado')

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
                time.sleep(2)

                del self.suministros_activos[cp_id]

    def manejar_desconexion_monitor(self, cp_id: str):
        """
        Llamado desde servidor_socket cuando un Monitor se desconecta.
        Marca el CP como desconectado pero NO finaliza suministros (continúan en Engine).
        Monitor_KO => desconectado (gris)
        """
        print(f"\n[DESCONEXIÓN] Monitor de CP {cp_id} desconectado")

        self.db.actualizar_estado_cp(cp_id, 'desconectado')
        self._publicar_estado_cp(cp_id, 'desconectado')

        # NO finalizar el suministro - el Engine sigue funcionando
        # El suministro se recuperará cuando el Monitor se reconecte
        if cp_id in self.suministros_activos:
            info = self.suministros_activos[cp_id]
            print(f"[INFO] CP {cp_id} tiene suministro activo (ID: {info['suministro_id']})")
            print(f"[INFO] El suministro continuará en el Engine y se recuperará al reconectar")

            # NO eliminar de memoria ni finalizar en BD - se recuperará después

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

