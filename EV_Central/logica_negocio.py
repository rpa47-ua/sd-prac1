# Módulo de lógica de negocio: Implementa todas las reglas y validaciones del sistema
# Procesa solicitudes de suministro, telemetría, averías, recuperación y gestión de colas

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
        self.lock = threading.Lock()

    def recuperar_suministros_al_inicio(self):
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

            self.kafka.enviar_mensaje('tickets', {
                'conductor_id': conductor_id,
                'cp_id': cp_id,
                'suministro_id': suministro_id,
                'consumo_kwh': consumo_kwh,
                'importe_total': importe_total
            })
            time.sleep(2)

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
        print(f"[AUTENTICACIÓN] CP {cp_id} conectándose...")

        try:
            cp = self.db.obtener_cp(cp_id)

            if not cp:
                print(f"[REGISTRO] Nuevo CP: {cp_id}")
                self.db.registrar_cp(cp_id)
            else:
                print(f"[RECONEXIÓN] CP {cp_id} reconectándose (estado: {cp.get('estado', 'desconocido')})")

            print(f"[OK] Monitor de CP {cp_id} autenticado")
            return True

        except Exception as e:
            print(f"[ERROR] Error autenticando CP {cp_id}: {e}")
            return False

    def procesar_solicitud_suministro(self, mensaje: dict):
        conductor_id = mensaje.get('conductor_id')
        cp_id = mensaje.get('cp_id')
        origen = mensaje.get('origen', 'CONDUCTOR')
        time_to_end = mensaje.get('time_to_end')

        print(f"\nProcesando solicitud [{origen}]: Conductor {conductor_id} -> CP {cp_id}")
        if time_to_end:
            print(f"  Tiempo límite solicitado: {time_to_end}s")

        # 1. Verificar que el conductor existe y está conectado
        conductor = self.db.obtener_conductor(conductor_id)
        if not conductor:
            print(f"[ERROR] Conductor {conductor_id} no registrado en el sistema")
            self._enviar_respuesta_solicitud(conductor_id, cp_id, False, "Conductor no registrado", origen, None, time_to_end)
            return

        if not conductor.get('conectado', False):
            print(f"[ERROR] Conductor {conductor_id} no está conectado")
            self._enviar_respuesta_solicitud(conductor_id, cp_id, False, "Conductor no conectado", origen, None, time_to_end)
            return

        # 2. Verificar que el CP existe
        cp = self.db.obtener_cp(cp_id)
        if not cp:
            print(f"[ERROR] CP {cp_id} no existe")
            self._enviar_respuesta_solicitud(conductor_id, cp_id, False, "CP no encontrado", origen, None, time_to_end)
            return

        # 3. Verificar que el CP esta disponible
        if cp['estado'] != 'activado':
            print(f"[INFO] CP {cp_id} no esta disponible (estado: {cp['estado']})")

            if cp['estado'] == 'suministrando':
                with self.lock: 
                    if cp_id not in self.colas_espera:
                        self.colas_espera[cp_id] = []

                    self.colas_espera[cp_id].append({
                        'conductor_id': conductor_id,
                        'origen': origen,
                        'time_to_end': time_to_end
                    })

                    posicion = len(self.colas_espera[cp_id])
                print(f"[COLA] Conductor {conductor_id} añadido a la cola de {cp_id} (posición {posicion})")
                self._enviar_respuesta_solicitud(conductor_id, cp_id, False, f"CP ocupado. En cola, posición {posicion}", origen, None, time_to_end)
            else:
                print(f"[RECHAZO] Solicitud rechazada para {cp_id} (estado: {cp['estado']})")
                self._enviar_respuesta_solicitud(conductor_id, cp_id, False, f"CP no disponible: {cp['estado']}", origen, None, time_to_end)
            return

        # 4. Todo OK - Crear suministro y autorizar
        suministro_id = self.db.crear_suministro(conductor_id, cp_id)
        self.db.actualizar_estado_cp(cp_id, 'suministrando')

        with self.lock:
            self.suministros_activos[cp_id] = {
                'conductor_id': conductor_id,
                'suministro_id': suministro_id,
                'consumo_actual': 0.0,
                'importe_actual': 0.0
            }

        print(f"[OK] Suministro autorizado (ID: {suministro_id})")

        # 5. Notificar según el origen
        self._enviar_respuesta_solicitud(conductor_id, cp_id, True, "Suministro autorizado", origen, suministro_id, time_to_end)

        # 6. Notificar al CP para que inicie el suministro
        comando = {
            'tipo': 'INICIAR_SUMINISTRO',
            'cp_id': cp_id,
            'conductor_id': conductor_id,
            'suministro_id': suministro_id
        }

        if time_to_end is not None:
            comando['time_to_end'] = time_to_end

        self.kafka.enviar_mensaje('comandos_cp', comando)
        
        time.sleep(2)

    def _enviar_respuesta_solicitud(self, conductor_id: str, cp_id: str, autorizado: bool, mensaje: str, origen: str, suministro_id: int, time_to_end=None):
        if origen == 'CP':
            respuesta = {
                'cp_id': cp_id,
                'conductor_id': conductor_id,
                'autorizado': autorizado,
                'mensaje': mensaje,
                'suministro_id': suministro_id
            }
            if time_to_end is not None:
                respuesta['time_to_end'] = time_to_end
                
            self.kafka.enviar_mensaje('respuestas_cp', respuesta)
            time.sleep(2)
        else:
            respuesta = {
                'conductor_id': conductor_id,
                'cp_id': cp_id,
                'autorizado': autorizado,
                'mensaje': mensaje,
                'suministro_id': suministro_id
            }
            if time_to_end is not None:
                respuesta['time_to_end'] = time_to_end
                
            self.kafka.enviar_mensaje('respuestas_conductor', respuesta)
            time.sleep(2)

    def _procesar_siguiente_en_cola(self, cp_id: str):
        with self.lock: 
            if cp_id not in self.colas_espera or len(self.colas_espera[cp_id]) == 0:
                print(f"[COLA] No hay solicitudes en espera para {cp_id}")
                return

            siguiente = self.colas_espera[cp_id].pop(0)
            conductor_id = siguiente['conductor_id']
            origen = siguiente['origen']
            time_to_end = siguiente.get('time_to_end')

        print(f"[COLA] Procesando siguiente en cola: Conductor {conductor_id} -> CP {cp_id}")

        conductor = self.db.obtener_conductor(conductor_id)
        if not conductor or not conductor.get('conectado', False):
            print(f"[COLA] Conductor {conductor_id} ya no está conectado. Procesando siguiente en cola...")
            self._procesar_siguiente_en_cola(cp_id)
            return

        cp = self.db.obtener_cp(cp_id)
        if not cp or cp['estado'] != 'activado':
            print(f"[ERROR] CP {cp_id} no disponible para procesar cola")
            with self.lock:
                self.colas_espera[cp_id].insert(0, siguiente)
            return

        suministro_id = self.db.crear_suministro(conductor_id, cp_id)
        self.db.actualizar_estado_cp(cp_id, 'suministrando')

        with self.lock: 
            self.suministros_activos[cp_id] = {
                'conductor_id': conductor_id,
                'suministro_id': suministro_id,
                'consumo_actual': 0.0,
                'importe_actual': 0.0
            }

        print(f"[OK] Suministro autorizado desde cola (ID: {suministro_id})")

        self._enviar_respuesta_solicitud(conductor_id, cp_id, True, "Suministro autorizado (desde cola)", origen, suministro_id, time_to_end)

        comando = {
            'tipo': 'INICIAR_SUMINISTRO',
            'cp_id': cp_id,
            'conductor_id': conductor_id,
            'suministro_id': suministro_id
        }

        if time_to_end is not None:
            comando['time_to_end'] = time_to_end

        self.kafka.enviar_mensaje('comandos_cp', comando)

        time.sleep(2)

    def procesar_telemetria_cp(self, mensaje: dict):
        cp_id = mensaje.get('cp_id')
        conductor_id = mensaje.get('conductor_id')
        consumo_actual = mensaje.get('consumo_actual', 0.0)
        importe_actual = mensaje.get('importe_actual', 0.0)

        with self.lock:  
            if cp_id in self.suministros_activos:
                self.suministros_activos[cp_id]['consumo_actual'] = consumo_actual
                self.suministros_activos[cp_id]['importe_actual'] = importe_actual

                suministro_id = self.suministros_activos[cp_id]['suministro_id']
                self.db.actualizar_suministro(suministro_id, consumo_actual, importe_actual)
            else:
                suministro = self.db.obtener_suministro_activo(cp_id)
                if suministro:
                    print(f"[RECUPERACIÓN] Telemetría recibida para {cp_id} sin suministro en memoria, recuperando de BD...")
                    self.suministros_activos[cp_id] = {
                        'conductor_id': suministro['conductor_id'],
                        'suministro_id': suministro['id'],
                        'consumo_actual': consumo_actual,
                        'importe_actual': importe_actual
                    }
                    self.db.actualizar_suministro(suministro['id'], consumo_actual, importe_actual)
                    print(f"  [OK] Recuperado suministro ID {suministro['id']} con telemetría actual")

    def procesar_fin_suministro(self, mensaje: dict):
        cp_id = mensaje.get('cp_id')
        conductor_id = mensaje.get('conductor_id')
        suministro_id = mensaje.get('suministro_id')
        consumo_kwh = mensaje.get('consumo_kwh', 0.0)
        importe = mensaje.get('importe_total', 0.0) 

        print(f"\n[FIN] Finalizando suministro en {cp_id}")

        with self.lock:
            if cp_id in self.suministros_activos:
                info = self.suministros_activos[cp_id]
                suministro_id_memoria = info['suministro_id']
                conductor_id_memoria = info['conductor_id']

                if suministro_id and suministro_id != suministro_id_memoria:
                    print(f"[AVISO] Suministro ID inconsistente: Engine={suministro_id}, Memoria={suministro_id_memoria}")

                final_suministro_id = suministro_id_memoria
                final_conductor_id = conductor_id_memoria

                del self.suministros_activos[cp_id]
            else:
                final_suministro_id = suministro_id
                final_conductor_id = conductor_id

        if final_suministro_id and final_conductor_id:
            self.db.finalizar_suministro(final_suministro_id, consumo_kwh, importe)

            self.kafka.enviar_mensaje('tickets', {
                'conductor_id': final_conductor_id,
                'cp_id': cp_id,
                'suministro_id': final_suministro_id,
                'consumo_kwh': consumo_kwh,
                'importe_total': importe
            })
            time.sleep(2)

            self.db.marcar_ticket_enviado(final_suministro_id)

            print(f"[OK] Suministro finalizado. Ticket enviado a {final_conductor_id}")
            print(f"[ESPERA] CP {cp_id} esperará 4 segundos antes de estar disponible de nuevo...")

            def activar_tras_espera():
                time.sleep(4)
                cp_actual = self.db.obtener_cp(cp_id)
                if cp_actual and cp_actual['estado'] == 'suministrando':
                    self.db.actualizar_estado_cp(cp_id, 'activado')
                    print(f"[OK] CP {cp_id} disponible de nuevo tras período de espera")
                    self._procesar_siguiente_en_cola(cp_id)

            threading.Thread(target=activar_tras_espera, daemon=True).start()
        else:
            print(f"[AVISO] Fin de suministro recibido pero no hay datos completos para procesar")

    def procesar_averia_cp(self, mensaje: dict):
        cp_id = mensaje.get('cp_id')
        descripcion = mensaje.get('descripcion', 'Averia desconocida')

        print(f"\n[AVISO] AVERIA en {cp_id}: {descripcion}")

        self.db.actualizar_estado_cp(cp_id, 'averiado')

        with self.lock:  
            if cp_id in self.suministros_activos:
                info = self.suministros_activos[cp_id]
                conductor_id_emergencia = info['conductor_id']

                self.db.finalizar_suministro(
                    info['suministro_id'],
                    info['consumo_actual'],
                    info['importe_actual']
                )

                del self.suministros_activos[cp_id]
            else:
                conductor_id_emergencia = None

        if conductor_id_emergencia:
            self.kafka.enviar_mensaje('notificaciones', {
                'tipo': 'AVERIA_DURANTE_SUMINISTRO',
                'conductor_id': conductor_id_emergencia,
                'cp_id': cp_id,
                'mensaje': 'Suministro interrumpido por avería'
            })
            time.sleep(2)

    def procesar_recuperacion_cp(self, mensaje: dict):
        cp_id = mensaje.get('cp_id')
        print(f"\n[OK] CP {cp_id} recuperado de averia")

        self.db.actualizar_estado_cp(cp_id, 'activado')

    def procesar_registro_conductor(self, mensaje: dict):
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
            suministro = self.db.obtener_suministro_activo_conductor(conductor_id)
            if suministro:
                print(f"[RECUPERACION] Suministro activo encontrado (ID: {suministro['id']}, CP: {suministro['cp_id']})")
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
        cp_id = mensaje.get('cp_id')
        activo = mensaje.get('activo', False)

        if activo:
            conductor_id = mensaje.get('conductor_id')
            suministro_id = mensaje.get('suministro_id')
            consumo_actual = mensaje.get('consumo_actual', 0.0)
            importe_actual = mensaje.get('importe_actual', 0.0)

            print(f"[RECUPERACIÓN] Engine {cp_id} reporta suministro activo (ID: {suministro_id})")

            with self.lock: 
                self.suministros_activos[cp_id] = {
                    'conductor_id': conductor_id,
                    'suministro_id': suministro_id,
                    'consumo_actual': consumo_actual,
                    'importe_actual': importe_actual
                }

            self.db.actualizar_suministro(suministro_id, consumo_actual, importe_actual)
            print(f"  [OK] Suministro recuperado: {consumo_actual} kWh, {importe_actual} €")
        else:
            print(f"[INFO] Engine {cp_id} no tiene suministro activo")

    def procesar_estado_engine(self, cp_id: str, estado_engine: str):
        print(f"[DEBUG] Recibido estado '{estado_engine}' para CP {cp_id}")

        cp = self.db.obtener_cp(cp_id)
        if not cp:
            print(f"[ERROR] CP {cp_id} no encontrado en BD al procesar estado")
            return

        estado_actual = cp['estado']
        print(f"[DEBUG] Estado actual del CP {cp_id} en BD: {estado_actual}")

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

            with self.lock:  
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

            with self.lock:
                if cp_id in self.suministros_activos:
                    info = self.suministros_activos[cp_id]
                    conductor_id_averia = info['conductor_id']
                    print(f"[AVERIA] Suministro activo en {cp_id} interrumpido por avería")
                    print(f"[INFO] Se esperará a que el Engine se recupere para enviar el ticket final")
                else:
                    conductor_id_averia = None

            if conductor_id_averia:
                self.kafka.enviar_mensaje('notificaciones', {
                    'tipo': 'AVERIA_ENGINE',
                    'conductor_id': conductor_id_averia,
                    'cp_id': cp_id,
                    'mensaje': f'Suministro interrumpido: Engine de CP {cp_id} averiado'
                })
                time.sleep(2)

    def manejar_desconexion_monitor(self, cp_id: str):
        print(f"\n[DESCONEXIÓN] Monitor de CP {cp_id} desconectado")

        self.db.actualizar_estado_cp(cp_id, 'desconectado')
        self._publicar_estado_cp(cp_id, 'desconectado')

        with self.lock:  
            if cp_id in self.suministros_activos:
                info = self.suministros_activos[cp_id]
                print(f"[INFO] CP {cp_id} tiene suministro activo (ID: {info['suministro_id']})")
                print(f"[INFO] El suministro continuará en el Engine y se recuperará al reconectar")


    def parar_cp(self, cp_id: str):
        print(f"[STOP] Parando CP {cp_id}")

        resultado = self.db.actualizar_estado_cp(cp_id, 'parado')
        print(f"[DEBUG] Estado 'parado' actualizado en BD: {resultado}")

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
        print(f"[PLAY] Reanudando CP {cp_id}")

        resultado = self.db.actualizar_estado_cp(cp_id, 'desconectado')
        print(f"[DEBUG] Estado actualizado en BD: {resultado}")

        if self.servidor_socket:
            comando = {'tipo': 'REANUDAR', 'cp_id': cp_id}
            enviado = self.servidor_socket.enviar_a_cp(cp_id, comando)
            if enviado:
                print(f"[OK] Comando REANUDAR enviado al Monitor de {cp_id}")
            else:
                print(f"[ERROR] No se pudo enviar comando REANUDAR al Monitor de {cp_id}")
        else:
            print(f"[ERROR] Servidor socket no disponible para enviar comando")

    def parar_todos_cps(self):
        cps = self.db.obtener_todos_los_cps()

        for cp in cps:
            if cp['estado'] in ['activado', 'suministrando']:
                self.parar_cp(cp['id'])

        print(f"[STOP ALL] Comando de parada enviado a todos los CPs activos")

    def reanudar_todos_cps(self):
        cps = self.db.obtener_todos_los_cps()

        for cp in cps:
            if cp['estado'] == 'parado':
                self.reanudar_cp(cp['id'])

        print(f"[PLAY ALL] Comando de reanudación enviado a todos los CPs parados")

    def obtener_estado_sistema(self):
        with self.lock: 
            suministros_copy = self.suministros_activos.copy()

        return {
            'cps': self.db.obtener_todos_los_cps(),
            'suministros_activos': suministros_copy
        }

