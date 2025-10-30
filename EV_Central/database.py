"""Gestión de base de datos para EV_Central"""
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
            # Crear pool de conexiones (en lugar de una sola conexión)
            self.pool = PooledDB(
                creator=pymysql,
                maxconnections=20,  # Máximo 20 conexiones simultáneas
                mincached=2,        # Mínimo 2 conexiones en cache
                maxcached=10,       # Máximo 10 conexiones en cache
                blocking=True,      # Bloquear si no hay conexiones disponibles
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
        """Obtiene una conexión del pool"""
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
                conn.close()  # Devolver al pool
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
        """
        Registra un nuevo Charging Point en BBDD
        El CP envía sus propios datos (coordenadas, precio) directamente
        """
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
        """Registra un conductor en BBDD"""
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
        """Actualiza el estado de conexión de un conductor"""
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
        """Obtiene el suministro activo de un conductor específico"""
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
        """Obtiene todos los suministros activos (para recuperación tras reinicio)"""
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
        """Marca todos los CPs como desconectados (usado al arrancar Central)"""
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
        """Obtiene suministros finalizados sin ticket enviado"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    # Verificar si la columna ticket_enviado existe
                    cursor.execute("SHOW COLUMNS FROM suministros LIKE 'ticket_enviado'")
                    if cursor.fetchone():
                        cursor.execute("""SELECT * FROM suministros
                                         WHERE estado = 'completado' AND ticket_enviado = FALSE
                                         ORDER BY fecha_fin DESC""")
                        return cursor.fetchall()
                    else:
                        # Si no existe la columna, asumir que ningún ticket ha sido enviado
                        print("[INFO] Columna ticket_enviado no existe. Recrear BD con nuevo schema.")
                        return []
            finally:
                conn.close()
        except Exception as e:
            print(f"Error obteniendo suministros pendientes de ticket: {e}")
            return []

    def marcar_ticket_enviado(self, suministro_id: int):
        """Marca un suministro como ticket enviado"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    # Verificar si la columna existe antes de actualizar
                    cursor.execute("SHOW COLUMNS FROM suministros LIKE 'ticket_enviado'")
                    if cursor.fetchone():
                        cursor.execute("UPDATE suministros SET ticket_enviado = TRUE WHERE id = %s", (suministro_id,))
                    return True
            finally:
                conn.close()
        except Exception as e:
            print(f"Error marcando ticket como enviado: {e}")
            return False