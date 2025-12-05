# Módulo de auditoría - Registra eventos del sistema para seguridad y trazabilidad
# Implementa registro automático de todas las acciones críticas en la base de datos

from json import dumps
from datetime import datetime


class SistemaAuditoria:
    def __init__(self, db):
        self.db = db
        self.modulo = 'EV_Central'

    def registrar_evento(self, accion: str, parametros: dict = None, resultado: str = 'exito',
                        detalle: str = None, ip_origen: str = 'localhost'):
        """
        Registra un evento en el sistema de auditoría

        Args:
            accion: Tipo de acción realizada (ej: 'autenticacion_cp', 'inicio_suministro')
            parametros: Diccionario con parámetros de la acción
            resultado: 'exito' o 'error'
            detalle: Descripción adicional del evento
            ip_origen: IP del origen de la acción
        """
        try:
            parametros_json = dumps(parametros) if parametros else None

            self.db.registrar_auditoria(
                ip_origen=ip_origen,
                modulo=self.modulo,
                accion=accion,
                parametros=parametros_json,
                resultado=resultado,
                detalle=detalle
            )
        except Exception as e:
            print(f"[AUDITORÍA] Error registrando evento: {e}")

    # === MÉTODOS ESPECÍFICOS PARA EVENTOS COMUNES ===

    def registrar_autenticacion_cp(self, cp_id: str, exito: bool, ip: str = 'localhost'):
        """Registra intento de autenticación de un CP"""
        self.registrar_evento(
            accion='autenticacion_cp',
            parametros={'cp_id': cp_id},
            resultado='exito' if exito else 'error',
            detalle=f'CP {cp_id} {"autenticado correctamente" if exito else "rechazado"}',
            ip_origen=ip
        )

    def registrar_inicio_suministro(self, conductor_id: str, cp_id: str, suministro_id: int):
        """Registra el inicio de un suministro"""
        self.registrar_evento(
            accion='inicio_suministro',
            parametros={'conductor_id': conductor_id, 'cp_id': cp_id, 'suministro_id': suministro_id},
            resultado='exito',
            detalle=f'Suministro {suministro_id} iniciado - Conductor {conductor_id} en {cp_id}'
        )

    def registrar_fin_suministro(self, suministro_id: int, consumo: float, importe: float, motivo: str = 'normal'):
        """Registra la finalización de un suministro"""
        self.registrar_evento(
            accion='fin_suministro',
            parametros={'suministro_id': suministro_id, 'consumo_kwh': consumo, 'importe': importe, 'motivo': motivo},
            resultado='exito',
            detalle=f'Suministro {suministro_id} finalizado - {consumo} kWh, {importe}€ (motivo: {motivo})'
        )

    def registrar_averia_cp(self, cp_id: str):
        """Registra una avería en un CP"""
        self.registrar_evento(
            accion='averia_cp',
            parametros={'cp_id': cp_id},
            resultado='error',
            detalle=f'CP {cp_id} reportó avería'
        )

    def registrar_recuperacion_cp(self, cp_id: str):
        """Registra la recuperación de un CP averiado"""
        self.registrar_evento(
            accion='recuperacion_cp',
            parametros={'cp_id': cp_id},
            resultado='exito',
            detalle=f'CP {cp_id} se recuperó de avería'
        )

    def registrar_desconexion_cp(self, cp_id: str, tenia_suministro: bool):
        """Registra la desconexión de un CP"""
        self.registrar_evento(
            accion='desconexion_cp',
            parametros={'cp_id': cp_id, 'tenia_suministro': tenia_suministro},
            resultado='exito' if not tenia_suministro else 'error',
            detalle=f'CP {cp_id} desconectado' + (' con suministro activo' if tenia_suministro else '')
        )

    def registrar_comando_cp(self, cp_id: str, comando: str, exito: bool):
        """Registra el envío de un comando a un CP"""
        self.registrar_evento(
            accion='comando_cp',
            parametros={'cp_id': cp_id, 'comando': comando},
            resultado='exito' if exito else 'error',
            detalle=f'Comando {comando} enviado a {cp_id}'
        )

    def registrar_registro_conductor(self, conductor_id: str):
        """Registra el alta de un nuevo conductor"""
        self.registrar_evento(
            accion='registro_conductor',
            parametros={'conductor_id': conductor_id},
            resultado='exito',
            detalle=f'Conductor {conductor_id} registrado en el sistema'
        )

    def registrar_alerta_meteorologica(self, cp_id: str, estado_clima: str):
        """Registra una alerta meteorológica recibida"""
        self.registrar_evento(
            accion='alerta_meteorologica',
            parametros={'cp_id': cp_id, 'estado': estado_clima},
            resultado='exito',
            detalle=f'Alerta meteorológica para {cp_id}: {estado_clima}'
        )

    def registrar_generacion_clave(self, cp_id: str):
        """Registra la generación de una nueva clave de cifrado para un CP"""
        self.registrar_evento(
            accion='generacion_clave_cifrado',
            parametros={'cp_id': cp_id},
            resultado='exito',
            detalle=f'Nueva clave de cifrado generada para {cp_id}'
        )

    def registrar_restauracion_clave(self, cp_id: str, exito: bool):
        """Registra la restauración de una clave de cifrado"""
        self.registrar_evento(
            accion='restauracion_clave_cifrado',
            parametros={'cp_id': cp_id},
            resultado='exito' if exito else 'error',
            detalle=f'Clave de cifrado {"restaurada" if exito else "no encontrada"} para {cp_id}'
        )

    def registrar_suministro_completo(self, suministro_id: int, conductor_id: str, cp_id: str, 
                                    consumo_kwh: float, importe: float, duracion: float = None):
        """Registra un suministro completo en auditoría"""
        parametros = {
            'suministro_id': suministro_id,
            'conductor_id': conductor_id,
            'cp_id': cp_id,
            'consumo_kwh': consumo_kwh,
            'importe': importe
        }
        
        if duracion:
            parametros['duracion_segundos'] = duracion
            
        detalle = f'Suministro {suministro_id}: {conductor_id} -> {cp_id} | {consumo_kwh:.3f} kWh, {importe:.2f}€'
        if duracion:
            detalle += f' | Duración: {duracion:.1f}s'
            
        self.registrar_evento(
            accion='suministro_completado',
            parametros=parametros,
            resultado='exito',
            detalle=detalle
        )

    def registrar_suministro_interrumpido(self, suministro_id: int, conductor_id: str, cp_id: str,
                                        consumo_kwh: float, importe: float, motivo: str):
        """Registra un suministro interrumpido por error"""
        self.registrar_evento(
            accion='suministro_interrumpido',
            parametros={
                'suministro_id': suministro_id,
                'conductor_id': conductor_id,
                'cp_id': cp_id,
                'consumo_kwh': consumo_kwh,
                'importe': importe,
                'motivo': motivo
            },
            resultado='error',
            detalle=f'Suministro {suministro_id} interrumpido - {conductor_id} en {cp_id}: {motivo}'
        )

    def registrar_suministro_rechazado(self, conductor_id: str, cp_id: str, motivo: str):
        """Registra un suministro rechazado"""
        self.registrar_evento(
            accion='suministro_rechazado',
            parametros={'conductor_id': conductor_id, 'cp_id': cp_id, 'motivo': motivo},
            resultado='error',
            detalle=f'Suministro rechazado - {conductor_id} en {cp_id}: {motivo}'
        )

    def registrar_suministro_en_cola(self, conductor_id: str, cp_id: str, posicion: int):
        """Registra un conductor añadido a la cola de espera"""
        self.registrar_evento(
            accion='suministro_en_cola',
            parametros={'conductor_id': conductor_id, 'cp_id': cp_id, 'posicion_cola': posicion},
            resultado='exito',
            detalle=f'Conductor {conductor_id} en cola para {cp_id} (posición {posicion})'
        )

    def registrar_error_cifrado(self, cp_id: str, tipo_error: str):
        """Registra un error de cifrado/descifrado"""
        self.registrar_evento(
            accion='error_cifrado',
            parametros={'cp_id': cp_id, 'tipo_error': tipo_error},
            resultado='error',
            detalle=f'Error de cifrado en CP {cp_id}: {tipo_error}'
        )