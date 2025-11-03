# Módulo servidor socket TCP: Acepta conexiones de Monitores de CPs vía socket
# Maneja autenticación, mantiene conexiones persistentes y detecta desconexiones

import socket
import threading
from json import dumps, loads


class ServidorSocket:
    def __init__(self, puerto: int, callback_autenticacion=None, callback_desconexion=None, callback_estado=None):
        self.puerto = puerto
        self.server_socket = None
        self.running = False
        self.clientes_conectados = {}
        self.callback_autenticacion = callback_autenticacion
        self.callback_desconexion = callback_desconexion
        self.callback_estado = callback_estado

    def iniciar(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.puerto))
            self.server_socket.listen(10)
            self.running = True

            print(f"[OK] Servidor Socket escuchando en puerto {self.puerto}")

            thread = threading.Thread(target=self._aceptar_conexiones, daemon=True)
            thread.start()
            return True

        except Exception as e:
            print(f"[ERROR] Error iniciando servidor socket: {e}")
            return False

    def _aceptar_conexiones(self):
        print(f"[SERVIDOR] Esperando conexiones en puerto {self.puerto}...")
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"[CONEXIÓN] Nueva conexión desde {address}")

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
        try:
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                client_socket.close()
                return

            mensaje = loads(data)

            if mensaje.get('tipo') == 'AUTENTICACION':
                cp_id = mensaje.get('cp_id')

                if self.callback_autenticacion:
                    resultado = self.callback_autenticacion(cp_id)

                    if resultado:
                        self.clientes_conectados[cp_id] = client_socket
                        respuesta = {
                            'tipo': 'AUTH_OK',
                            'mensaje': f'CP {cp_id} autenticado correctamente'
                        }
                        client_socket.send(dumps(respuesta).encode('utf-8'))
                        print(f"[OK] CP {cp_id} autenticado via socket")

                        self._mantener_conexion(client_socket, cp_id)
                    else:
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
        try:
            client_socket.settimeout(3.0)

            while self.running:
                try:
                    data = client_socket.recv(4096)

                    if not data:
                        print(f"[SOCKET] CP {cp_id} cerró la conexión")
                        break

                    try:
                        mensaje = loads(data.decode('utf-8'))

                        if mensaje.get('tipo') == 'DESCONEXION':
                            print(f"[SOCKET] CP {cp_id} envió desconexión explícita")
                            break

                        if mensaje.get('tipo') in ['OK', 'AVERIA', 'SUMINISTRANDO', 'PARADO'] and self.callback_estado:
                            estado_engine = mensaje.get('tipo')
                            self.callback_estado(cp_id, estado_engine)
                    except:
                        pass

                except socket.timeout:
                    continue
                except socket.error as e:
                    print(f"[SOCKET] Error de conexión con {cp_id}: {e}")
                    break

        except Exception as e:
            print(f"[SOCKET] Conexión con {cp_id} perdida: {e}")
        finally:
            if cp_id in self.clientes_conectados:
                del self.clientes_conectados[cp_id]
            client_socket.close()

            if self.callback_desconexion:
                self.callback_desconexion(cp_id)

            print(f"[SOCKET] {cp_id} desconectado del servidor")

    def obtener_cps_conectados(self):
        return list(self.clientes_conectados.keys())

    def enviar_a_cp(self, cp_id: str, mensaje: dict):
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
        self.running = False
        for socket_cp in self.clientes_conectados.values():
            socket_cp.close()
        if self.server_socket:
            self.server_socket.close()
        print("[OK] Servidor socket detenido")