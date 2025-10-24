"""Gestión de base de datos para EV_Central"""
import pymysql
from typing import List, Dict, Optional


class Database:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    def conectar(self):
        try:
            self.connection = pymysql.connect(
                host=self.host, port=self.port, user=self.user, password=self.password,
                database=self.database, charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor, autocommit=True
            )
            print(f"[OK] Conectado a BD {self.database}")
            return True
        except Exception as e:
            print(f"[ERROR] Error BD: {e}")
            return False

    def desconectar(self):
        if self.connection:
            self.connection.close()
            print("[OK] Desconectado de BD")

    def _verificar_conexion(self):
        """Verifica y restablece la conexión si es necesaria"""
        try:
            if self.connection:
                self.connection.ping(reconnect=True)
            else:
                self.conectar()
        except Exception:
            self.conectar()

    def obtener_todos_los_cps(self) -> List[Dict]:
        try:
            self._verificar_conexion()
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT * FROM charging_points")
                return cursor.fetchall()
        except Exception as e:
            print(f"Error obteniendo CPs: {e}")
            return []

    def obtener_cp(self, cp_id: str) -> Optional[Dict]:
        try:
            self._verificar_conexion()
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT * FROM charging_points WHERE id = %s", (cp_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"Error obteniendo CP: {e}")
            return None

    def registrar_cp(self, cp_id: str):
        """
        Registra un nuevo Charging Point en BBDD
        El CP envía sus propios datos (coordenadas, precio) directamente
        """
        try:
            with self.connection.cursor() as cursor:
                sql = """INSERT IGNORE INTO charging_points (id, estado)
                         VALUES (%s, 'desconectado')"""
                cursor.execute(sql, (cp_id,))
                print(f"[OK] CP {cp_id} registrado")
                return True
        except Exception as e:
            print(f"Error registrando CP: {e}")
            return False

    def actualizar_estado_cp(self, cp_id: str, estado: str):
        try:
            self._verificar_conexion()
            with self.connection.cursor() as cursor:
                cursor.execute("UPDATE charging_points SET estado = %s WHERE id = %s", (estado, cp_id))
                return True
        except Exception as e:
            print(f"Error actualizando estado: {e}")
            return False

    def obtener_conductor(self, conductor_id: str) -> Optional[Dict]:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT * FROM conductores WHERE id = %s", (conductor_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"Error obteniendo conductor: {e}")
            return None

    def registrar_conductor(self, conductor_id: str, conectado: bool = True):
        """Registra un conductor en BBDD"""
        try:
            with self.connection.cursor() as cursor:
                sql = """INSERT INTO conductores (id, conectado) VALUES (%s, %s)
                         ON DUPLICATE KEY UPDATE conectado = %s"""
                cursor.execute(sql, (conductor_id, conectado, conectado))
                return True
        except Exception as e:
            print(f"Error registrando conductor: {e}")
            return False

    def actualizar_estado_conductor(self, conductor_id: str, conectado: bool):
        """Actualiza el estado de conexión de un conductor"""
        try:
            self._verificar_conexion()
            with self.connection.cursor() as cursor:
                cursor.execute("UPDATE conductores SET conectado = %s WHERE id = %s", (conectado, conductor_id))
                return True
        except Exception as e:
            print(f"Error actualizando estado conductor: {e}")
            return False

    def crear_suministro(self, conductor_id: str, cp_id: str) -> Optional[int]:
        try:
            self._verificar_conexion()
            with self.connection.cursor() as cursor:
                cursor.execute("INSERT INTO suministros (conductor_id, cp_id, estado) VALUES (%s, %s, 'autorizado')",
                             (conductor_id, cp_id))
                return cursor.lastrowid
        except Exception as e:
            print(f"Error creando suministro: {e}")
            return None

    def actualizar_suministro(self, suministro_id: int, consumo_kwh: float, importe_total: float):
        try:
            self._verificar_conexion()
            with self.connection.cursor() as cursor:
                cursor.execute("UPDATE suministros SET consumo_kwh = %s, importe_total = %s, estado = 'en_curso' WHERE id = %s",
                             (consumo_kwh, importe_total, suministro_id))
                return True
        except Exception as e:
            print(f"Error actualizando suministro: {e}")
            return False

    def finalizar_suministro(self, suministro_id: int, consumo_kwh: float, importe_total: float):
        try:
            self._verificar_conexion()
            with self.connection.cursor() as cursor:
                cursor.execute("""UPDATE suministros SET consumo_kwh = %s, importe_total = %s,
                                 fecha_fin = CURRENT_TIMESTAMP, estado = 'completado' WHERE id = %s""",
                             (consumo_kwh, importe_total, suministro_id))
                return True
        except Exception as e:
            print(f"Error finalizando suministro: {e}")
            return False

    def obtener_suministro_activo(self, cp_id: str) -> Optional[Dict]:
        try:
            self._verificar_conexion()
            with self.connection.cursor() as cursor:
                cursor.execute("""SELECT * FROM suministros WHERE cp_id = %s AND estado IN ('autorizado', 'en_curso')
                                 ORDER BY fecha_inicio DESC LIMIT 1""", (cp_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"Error obteniendo suministro: {e}")
            return None

    def obtener_suministro_activo_conductor(self, conductor_id: str) -> Optional[Dict]:
        """Obtiene el suministro activo de un conductor específico"""
        try:
            self._verificar_conexion()
            with self.connection.cursor() as cursor:
                cursor.execute("""SELECT * FROM suministros WHERE conductor_id = %s AND estado IN ('autorizado', 'en_curso')
                                 ORDER BY fecha_inicio DESC LIMIT 1""", (conductor_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"Error obteniendo suministro activo conductor: {e}")
            return None

    def obtener_suministros_activos(self) -> List[Dict]:
        """Obtiene todos los suministros activos (para recuperación tras reinicio)"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""SELECT * FROM suministros
                                 WHERE estado IN ('autorizado', 'en_curso')
                                 ORDER BY fecha_inicio DESC""")
                return cursor.fetchall()
        except Exception as e:
            print(f"Error obteniendo suministros activos: {e}")
            return []

    def marcar_todos_cps_desconectados(self):
        """Marca todos los CPs como desconectados (usado al arrancar Central)"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("UPDATE charging_points SET estado = 'desconectado'")
                affected = cursor.rowcount
                print(f"[STARTUP] {affected} CPs marcados como desconectados")
                return True
        except Exception as e:
            print(f"Error marcando CPs como desconectados: {e}")
            return False

    def obtener_suministros_pendientes_ticket(self) -> List[Dict]:
        """Obtiene suministros finalizados sin ticket enviado"""
        try:
            self._verificar_conexion()
            with self.connection.cursor() as cursor:
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
        except Exception as e:
            print(f"Error obteniendo suministros pendientes de ticket: {e}")
            return []

    def marcar_ticket_enviado(self, suministro_id: int):
        """Marca un suministro como ticket enviado"""
        try:
            self._verificar_conexion()
            with self.connection.cursor() as cursor:
                # Verificar si la columna existe antes de actualizar
                cursor.execute("SHOW COLUMNS FROM suministros LIKE 'ticket_enviado'")
                if cursor.fetchone():
                    cursor.execute("UPDATE suministros SET ticket_enviado = TRUE WHERE id = %s", (suministro_id,))
                return True
        except Exception as e:
            print(f"Error marcando ticket como enviado: {e}")
            return False