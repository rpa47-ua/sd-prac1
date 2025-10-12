"""
Servidor Socket TCP para EV_Central
Acepta conexiones de los monitores de CP (EV_CP_M)
"""
import socket
import threading
from json import dumps, loads


class ServidorSocket:
    def __init__(self, puerto: int, callback_autenticacion=None, callback_desconexion=None, callback_estado=None):
        self.puerto = puerto
        self.server_socket = None
        self.running = False
        self.clientes_conectados = {}  # {cp_id: socket}
        self.callback_autenticacion = callback_autenticacion
        self.callback_desconexion = callback_desconexion  # Callback al desconectar
        self.callback_estado = callback_estado  # Callback para estados del Engine

    def iniciar(self):
        """Inicia el servidor socket"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.puerto))
            self.server_socket.listen(10)
            self.running = True

            print(f"[OK] Servidor Socket escuchando en puerto {self.puerto}")

            # Hilo para aceptar conexiones
            thread = threading.Thread(target=self._aceptar_conexiones, daemon=True)
            thread.start()
            return True

        except Exception as e:
            print(f"[ERROR] Error iniciando servidor socket: {e}")
            return False

    def _aceptar_conexiones(self):
        """Acepta conexiones entrantes en un bucle"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"Nueva conexion desde {address}")

                # Crear hilo para manejar este cliente
                thread = threading.Thread(
                    target=self._manejar_cliente,
                    args=(client_socket, address),
                    daemon=True
                )
                thread.start()

            except Exception as e:
                if self.running:
                    print(f"[ERROR] Error aceptando conexion: {e}")

    def _manejar_cliente(self, client_socket, address):
        """Maneja la comunicación con un cliente específico"""
        try:
            # Recibir mensaje de autenticación
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                client_socket.close()
                return

            mensaje = loads(data)

            if mensaje.get('tipo') == 'AUTENTICACION':
                cp_id = mensaje.get('cp_id')

                # Validar autenticación (llamar callback)
                if self.callback_autenticacion:
                    resultado = self.callback_autenticacion(cp_id)

                    if resultado:
                        # Autenticación exitosa
                        self.clientes_conectados[cp_id] = client_socket
                        respuesta = {
                            'tipo': 'AUTH_OK',
                            'mensaje': f'CP {cp_id} autenticado correctamente'
                        }
                        client_socket.send(dumps(respuesta).encode('utf-8'))
                        print(f"[OK] CP {cp_id} autenticado via socket")

                        # Mantener conexión abierta para futuras comunicaciones
                        self._mantener_conexion(client_socket, cp_id)
                    else:
                        # Autenticación fallida
                        respuesta = {
                            'tipo': 'AUTH_ERROR',
                            'mensaje': 'CP no válido'
                        }
                        client_socket.send(dumps(respuesta).encode('utf-8'))
                        client_socket.close()

        except Exception as e:
            print(f"[ERROR] Error manejando cliente {address}: {e}")
            client_socket.close()

    def _mantener_conexion(self, client_socket, cp_id):
        """
        Mantiene la conexión socket abierta para detectar desconexiones.
        Usa timeout para poder verificar periódicamente si el socket sigue vivo.
        """
        try:
            # Configurar timeout de 3 segundos para no quedarse bloqueado
            client_socket.settimeout(3.0)

            while self.running:
                try:
                    # Intentar recibir datos (con timeout)
                    data = client_socket.recv(4096)

                    if not data:
                        # Socket cerrado por el cliente
                        print(f"[SOCKET] CP {cp_id} cerró la conexión")
                        break

                    # Si el Monitor envía algún mensaje, procesarlo
                    try:
                        mensaje = loads(data.decode('utf-8'))

                        # Detectar desconexión explícita
                        if mensaje.get('tipo') == 'DESCONEXION':
                            print(f"[SOCKET] CP {cp_id} envió desconexión explícita")
                            break

                        # Detectar mensajes de estado del Engine
                        if mensaje.get('tipo') == 'ESTADO' and self.callback_estado:
                            estado_engine = mensaje.get('estado')
                            if estado_engine:
                                self.callback_estado(cp_id, estado_engine)
                        else:
                            print(f"[SOCKET DEBUG] Mensaje sin procesar de {cp_id}: {mensaje}")
                    except:
                        pass  # Ignorar mensajes mal formados

                except socket.timeout:
                    # Timeout normal, el socket sigue vivo, continuar esperando
                    continue
                except socket.error as e:
                    # Error de socket = desconexión
                    print(f"[SOCKET] Error de conexión con {cp_id}: {e}")
                    break

        except Exception as e:
            print(f"[SOCKET] Conexión con {cp_id} perdida: {e}")
        finally:
            # Limpiar conexión
            if cp_id in self.clientes_conectados:
                del self.clientes_conectados[cp_id]
            client_socket.close()

            # NUEVO: Notificar a lógica de negocio que el Monitor se desconectó
            if self.callback_desconexion:
                self.callback_desconexion(cp_id)

            print(f"[SOCKET] {cp_id} desconectado del servidor")

    def obtener_cps_conectados(self):
        """Retorna lista de CP IDs actualmente conectados"""
        return list(self.clientes_conectados.keys())

    def enviar_a_cp(self, cp_id: str, mensaje: dict):
        """Envía un mensaje a un CP específico vía socket"""
        if cp_id in self.clientes_conectados:
            try:
                socket_cp = self.clientes_conectados[cp_id]
                socket_cp.send(dumps(mensaje).encode('utf-8'))
                return True
            except Exception as e:
                print(f"[ERROR] Error enviando a {cp_id}: {e}")
                return False
        else:
            print(f"[AVISO] CP {cp_id} no esta conectado")
            return False

    def detener(self):
        """Detiene el servidor"""
        self.running = False
        for socket_cp in self.clientes_conectados.values():
            socket_cp.close()
        if self.server_socket:
            self.server_socket.close()
        print("[OK] Servidor socket detenido")
