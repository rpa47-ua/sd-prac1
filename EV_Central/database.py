# Módulo de gestión de base de datos: Maneja conexiones MySQL y operaciones CRUD
# Usa pool de conexiones para soportar concurrencia en CPs, conductores y suministros

import pymysql
from typing import List, Dict, Optional
from dbutils.pooled_db import PooledDB


class Database:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.pool = None

    def conectar(self):
        try:
            self.pool = PooledDB(
                creator=pymysql,
                maxconnections=20,
                mincached=2,
                maxcached=10,
                blocking=True,
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            print(f"[OK] Connection pool creado para BD {self.database}")
            print(f"[INFO] Pool: max=20 conexiones, min_cached=2, max_cached=10")
            return True
        except Exception as e:
            print(f"[ERROR] Error creando pool BD: {e}")
            return False

    def desconectar(self):
        if self.pool:
            self.pool.close()
            print("[OK] Connection pool cerrado")

    def _get_connection(self):
        if not self.pool:
            raise Exception("Pool de conexiones no inicializado")
        return self.pool.connection()

    def obtener_todos_los_cps(self) -> List[Dict]:
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM charging_points")
                    return cursor.fetchall()
            finally:
                conn.close()
        except Exception as e:
            print(f"Error obteniendo CPs: {e}")
            return []

    def obtener_cp(self, cp_id: str) -> Optional[Dict]:
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM charging_points WHERE id = %s", (cp_id,))
                    return cursor.fetchone()
            finally:
                conn.close()
        except Exception as e:
            print(f"Error obteniendo CP: {e}")
            return None

    def registrar_cp(self, cp_id: str):
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    sql = """INSERT IGNORE INTO charging_points (id, estado)
                             VALUES (%s, 'desconectado')"""
                    cursor.execute(sql, (cp_id,))
                    print(f"[OK] CP {cp_id} registrado")
                    return True
            finally:
                conn.close()
        except Exception as e:
            print(f"Error registrando CP: {e}")
            return False

    def actualizar_estado_cp(self, cp_id: str, estado: str):
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE charging_points SET estado = %s WHERE id = %s", (estado, cp_id))
                    return True
            finally:
                conn.close()
        except Exception as e:
            print(f"Error actualizando estado: {e}")
            return False

    def obtener_conductor(self, conductor_id: str) -> Optional[Dict]:
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM conductores WHERE id = %s", (conductor_id,))
                    return cursor.fetchone()
            finally:
                conn.close()
        except Exception as e:
            print(f"Error obteniendo conductor: {e}")
            return None

    def registrar_conductor(self, conductor_id: str, conectado: bool = True):
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    sql = """INSERT INTO conductores (id, conectado) VALUES (%s, %s)
                             ON DUPLICATE KEY UPDATE conectado = %s"""
                    cursor.execute(sql, (conductor_id, conectado, conectado))
                    return True
            finally:
                conn.close()
        except Exception as e:
            print(f"Error registrando conductor: {e}")
            return False

    def actualizar_estado_conductor(self, conductor_id: str, conectado: bool):
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE conductores SET conectado = %s WHERE id = %s", (conectado, conductor_id))
                    return True
            finally:
                conn.close()
        except Exception as e:
            print(f"Error actualizando estado conductor: {e}")
            return False

    def crear_suministro(self, conductor_id: str, cp_id: str) -> Optional[int]:
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("INSERT INTO suministros (conductor_id, cp_id, estado) VALUES (%s, %s, 'autorizado')",
                                 (conductor_id, cp_id))
                    return cursor.lastrowid
            finally:
                conn.close()
        except Exception as e:
            print(f"Error creando suministro: {e}")
            return None

    def actualizar_suministro(self, suministro_id: int, consumo_kwh: float, importe_total: float):
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE suministros SET consumo_kwh = %s, importe_total = %s, estado = 'en_curso' WHERE id = %s",
                                 (consumo_kwh, importe_total, suministro_id))
                    return True
            finally:
                conn.close()
        except Exception as e:
            print(f"Error actualizando suministro: {e}")
            return False

    def finalizar_suministro(self, suministro_id: int, consumo_kwh: float, importe_total: float):
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""UPDATE suministros SET consumo_kwh = %s, importe_total = %s,
                                     fecha_fin = CURRENT_TIMESTAMP, estado = 'completado' WHERE id = %s""",
                                 (consumo_kwh, importe_total, suministro_id))
                    return True
            finally:
                conn.close()
        except Exception as e:
            print(f"Error finalizando suministro: {e}")
            return False

    def obtener_suministro_activo(self, cp_id: str) -> Optional[Dict]:
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""SELECT * FROM suministros WHERE cp_id = %s AND estado IN ('autorizado', 'en_curso')
                                     ORDER BY fecha_inicio DESC LIMIT 1""", (cp_id,))
                    return cursor.fetchone()
            finally:
                conn.close()
        except Exception as e:
            print(f"Error obteniendo suministro: {e}")
            return None

    def obtener_suministro_activo_conductor(self, conductor_id: str) -> Optional[Dict]:
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""SELECT * FROM suministros WHERE conductor_id = %s AND estado IN ('autorizado', 'en_curso')
                                     ORDER BY fecha_inicio DESC LIMIT 1""", (conductor_id,))
                    return cursor.fetchone()
            finally:
                conn.close()
        except Exception as e:
            print(f"Error obteniendo suministro activo conductor: {e}")
            return None

    def obtener_suministros_activos(self) -> List[Dict]:
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""SELECT * FROM suministros
                                     WHERE estado IN ('autorizado', 'en_curso')
                                     ORDER BY fecha_inicio DESC""")
                    return cursor.fetchall()
            finally:
                conn.close()
        except Exception as e:
            print(f"Error obteniendo suministros activos: {e}")
            return []

    def marcar_todos_cps_desconectados(self):
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE charging_points SET estado = 'desconectado'")
                    affected = cursor.rowcount
                    print(f"[STARTUP] {affected} CPs marcados como desconectados")
                    return True
            finally:
                conn.close()
        except Exception as e:
            print(f"Error marcando CPs como desconectados: {e}")
            return False

    def obtener_suministros_pendientes_ticket(self) -> List[Dict]:
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SHOW COLUMNS FROM suministros LIKE 'ticket_enviado'")
                    if cursor.fetchone():
                        cursor.execute("""SELECT * FROM suministros
                                         WHERE estado = 'completado' AND ticket_enviado = FALSE
                                         ORDER BY fecha_fin DESC""")
                        return cursor.fetchall()
                    else:
                        print("[INFO] Columna ticket_enviado no existe. Recrear BD con nuevo schema.")
                        return []
            finally:
                conn.close()
        except Exception as e:
            print(f"Error obteniendo suministros pendientes de ticket: {e}")
            return []

    def marcar_ticket_enviado(self, suministro_id: int):
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SHOW COLUMNS FROM suministros LIKE 'ticket_enviado'")
                    if cursor.fetchone():
                        cursor.execute("UPDATE suministros SET ticket_enviado = TRUE WHERE id = %s", (suministro_id,))
                    return True
            finally:
                conn.close()
        except Exception as e:
            print(f"Error marcando ticket como enviado: {e}")
            return False

    # === MÉTODOS PARA CIFRADO Y SEGURIDAD (Release 2) ===

    def actualizar_clave_cifrado_cp(self, cp_id: str, clave_cifrado: str):
        """Actualiza la clave de cifrado de un CP"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""UPDATE charging_points
                                     SET clave_cifrado = %s, fecha_generacion_clave = CURRENT_TIMESTAMP
                                     WHERE id = %s""",
                                 (clave_cifrado, cp_id))
                    return True
            finally:
                conn.close()
        except Exception as e:
            print(f"Error actualizando clave de cifrado: {e}")
            return False

    def obtener_clave_cifrado_cp(self, cp_id: str) -> Optional[str]:
        """Obtiene la clave de cifrado de un CP"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT clave_cifrado FROM charging_points WHERE id = %s", (cp_id,))
                    result = cursor.fetchone()
                    return result['clave_cifrado'] if result else None
            finally:
                conn.close()
        except Exception as e:
            print(f"Error obteniendo clave de cifrado: {e}")
            return None

    # === MÉTODOS PARA DATOS METEOROLÓGICOS (Release 2) ===

    def actualizar_ubicacion_cp(self, cp_id: str, latitud: float, longitud: float):
        """Actualiza las coordenadas GPS de un CP"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""UPDATE charging_points
                                     SET latitud = %s, longitud = %s
                                     WHERE id = %s""",
                                 (latitud, longitud, cp_id))
                    return True
            finally:
                conn.close()
        except Exception as e:
            print(f"Error actualizando ubicación CP: {e}")
            return False

    def actualizar_clima_cp(self, cp_id: str, estado_meteorologico: str, alerta: bool = False):
        """Actualiza el estado meteorológico de un CP"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""UPDATE charging_points
                                     SET estado_meteorologico = %s, alerta_meteorologica = %s
                                     WHERE id = %s""",
                                 (estado_meteorologico, alerta, cp_id))
                    return True
            finally:
                conn.close()
        except Exception as e:
            print(f"Error actualizando clima CP: {e}")
            return False

    def obtener_cps_con_alerta_meteorologica(self) -> List[Dict]:
        """Obtiene todos los CPs con alerta meteorológica activa"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM charging_points WHERE alerta_meteorologica = TRUE")
                    return cursor.fetchall()
            finally:
                conn.close()
        except Exception as e:
            print(f"Error obteniendo CPs con alerta: {e}")
            return []

    # === MÉTODOS PARA AUDITORÍA (Release 2) ===

    def registrar_auditoria(self, ip_origen: str, modulo: str, accion: str,
                           parametros: str = None, resultado: str = 'exito', detalle: str = None):
        """Registra un evento en la tabla de auditoría"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""INSERT INTO auditoria
                                     (ip_origen, modulo, accion, parametros, resultado, detalle)
                                     VALUES (%s, %s, %s, %s, %s, %s)""",
                                 (ip_origen, modulo, accion, parametros, resultado, detalle))
                    return True
            finally:
                conn.close()
        except Exception as e:
            print(f"Error registrando auditoría: {e}")
            return False

    def obtener_auditoria(self, modulo: str = None, limit: int = 100) -> List[Dict]:
        """Obtiene registros de auditoría, opcionalmente filtrados por módulo"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    if modulo:
                        cursor.execute("""SELECT * FROM auditoria
                                         WHERE modulo = %s
                                         ORDER BY timestamp DESC LIMIT %s""",
                                     (modulo, limit))
                    else:
                        cursor.execute("SELECT * FROM auditoria ORDER BY timestamp DESC LIMIT %s", (limit,))
                    return cursor.fetchall()
            finally:
                conn.close()
        except Exception as e:
            print(f"Error obteniendo auditoría: {e}")
            return []