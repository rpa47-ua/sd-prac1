# Módulo de gestión criptográfica - Maneja cifrado simétrico AES para comunicación con CPs
# Cada CP tiene una clave única que se genera al autenticarse por primera vez

from cryptography.fernet import Fernet
from json import dumps, loads
import base64
import os


class CryptoManager:
    def __init__(self, db):
        self.db = db
        self.claves_cache = {}  # Cache de claves en memoria: {cp_id: Fernet_object}

    def generar_clave_para_cp(self, cp_id: str) -> str:
        """
        Genera una nueva clave de cifrado simétrica para un CP

        Returns:
            str: Clave en formato base64
        """
        clave = Fernet.generate_key()
        clave_str = clave.decode('utf-8')

        # Guardar en base de datos
        self.db.actualizar_clave_cifrado_cp(cp_id, clave_str)

        # Actualizar cache
        self.claves_cache[cp_id] = Fernet(clave)

        print(f"[CRYPTO] Nueva clave generada para {cp_id}")
        return clave_str

    def obtener_clave_cp(self, cp_id: str) -> Fernet:
        """
        Obtiene el objeto Fernet para un CP (desde cache o BD)

        Returns:
            Fernet: Objeto Fernet para cifrado/descifrado, o None si no existe
        """
        # Intentar obtener desde cache
        if cp_id in self.claves_cache:
            return self.claves_cache[cp_id]

        # Buscar en base de datos
        clave_str = self.db.obtener_clave_cifrado_cp(cp_id)

        if not clave_str:
            return None

        # Crear objeto Fernet y guardar en cache
        try:
            clave_bytes = clave_str.encode('utf-8')
            fernet_obj = Fernet(clave_bytes)
            self.claves_cache[cp_id] = fernet_obj
            return fernet_obj
        except Exception as e:
            print(f"[ERROR] Error creando objeto Fernet para {cp_id}: {e}")
            return None

    def cifrar_mensaje(self, cp_id: str, mensaje: dict) -> bytes:
        """
        Cifra un mensaje para enviar a un CP

        Args:
            cp_id: ID del CP
            mensaje: Diccionario con el mensaje a cifrar

        Returns:
            bytes: Mensaje cifrado, o None si falla
        """
        fernet = self.obtener_clave_cp(cp_id)

        if not fernet:
            print(f"[CRYPTO] No hay clave para {cp_id}, generando nueva...")
            self.generar_clave_para_cp(cp_id)
            fernet = self.obtener_clave_cp(cp_id)

        try:
            mensaje_json = dumps(mensaje)
            mensaje_cifrado = fernet.encrypt(mensaje_json.encode('utf-8'))
            return mensaje_cifrado
        except Exception as e:
            print(f"[ERROR] Error cifrando mensaje para {cp_id}: {e}")
            return None

    def descifrar_mensaje(self, cp_id: str, mensaje_cifrado: bytes) -> dict:
        """
        Descifra un mensaje recibido de un CP

        Args:
            cp_id: ID del CP
            mensaje_cifrado: Mensaje cifrado en bytes

        Returns:
            dict: Mensaje descifrado, o None si falla
        """
        fernet = self.obtener_clave_cp(cp_id)

        if not fernet:
            print(f"[ERROR] No hay clave para descifrar mensaje de {cp_id}")
            return None

        try:
            mensaje_descifrado = fernet.decrypt(mensaje_cifrado)
            mensaje_json = mensaje_descifrado.decode('utf-8')
            return loads(mensaje_json)
        except Exception as e:
            print(f"[ERROR] Error descifrando mensaje de {cp_id}: {e}")
            return None

    def restaurar_clave_cp(self, cp_id: str) -> bool:
        """
        Restaura la clave de cifrado de un CP desde la base de datos

        Returns:
            bool: True si se restauró correctamente, False si no existe
        """
        # Limpiar cache
        if cp_id in self.claves_cache:
            del self.claves_cache[cp_id]

        # Intentar obtener desde BD
        fernet = self.obtener_clave_cp(cp_id)

        if fernet:
            print(f"[CRYPTO] Clave restaurada para {cp_id}")
            return True
        else:
            print(f"[CRYPTO] No se encontró clave para {cp_id}")
            return False

    def limpiar_cache(self):
        """Limpia el cache de claves en memoria"""
        self.claves_cache.clear()
        print("[CRYPTO] Cache de claves limpiado")

    def obtener_claves_activas(self) -> list:
        """
        Obtiene la lista de CPs con claves activas en cache

        Returns:
            list: Lista de IDs de CPs con claves en cache
        """
        return list(self.claves_cache.keys())