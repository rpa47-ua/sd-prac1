# API REST para EV_Central - Expone endpoints para consultar estado del sistema
# Recibe alertas meteorológicas de EV_W y sirve datos al Frontend

from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os

# Añadir directorio padre para importar módulos de EV_Central
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from EV_Central.database import Database

app = Flask(__name__)
CORS(app)  # Permitir CORS para el frontend

# Base de datos
db = None

# === ENDPOINTS DE CONSULTA ===

@app.route('/api/status', methods=['GET'])
def get_status():
    """Endpoint para obtener estado general del sistema"""
    try:
        # Obtener todos los CPs
        cps = db.obtener_todos_los_cps()

        # Estadísticas de CPs por estado
        stats_cps = {
            'total': len(cps),
            'activos': sum(1 for cp in cps if cp['estado'] == 'activado'),
            'suministrando': sum(1 for cp in cps if cp['estado'] == 'suministrando'),
            'averiados': sum(1 for cp in cps if cp['estado'] == 'averiado'),
            'parados': sum(1 for cp in cps if cp['estado'] == 'parado'),
            'desconectados': sum(1 for cp in cps if cp['estado'] == 'desconectado')
        }

        # Obtener suministros activos
        suministros_activos = db.obtener_suministros_activos()

        return jsonify({
            'status': 'ok',
            'estadisticas_cps': stats_cps,
            'suministros_activos': len(suministros_activos),
            'cps_con_alerta': len(db.obtener_cps_con_alerta_meteorologica())
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)}), 500


@app.route('/api/cps', methods=['GET'])
def get_cps():
    """Endpoint para obtener lista de todos los CPs"""
    try:
        cps = db.obtener_todos_los_cps()

        # Convertir a formato JSON-friendly
        cps_data = []
        for cp in cps:
            cps_data.append({
                'id': cp['id'],
                'estado': cp['estado'],
                'fecha_registro': cp['fecha_registro'].isoformat() if cp['fecha_registro'] else None,
                'latitud': float(cp['latitud']) if cp.get('latitud') else None,
                'longitud': float(cp['longitud']) if cp.get('longitud') else None,
                'estado_meteorologico': cp.get('estado_meteorologico'),
                'alerta_meteorologica': bool(cp.get('alerta_meteorologica', False))
            })

        return jsonify({
            'status': 'ok',
            'cps': cps_data
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)}), 500


@app.route('/api/cps/<cp_id>', methods=['GET'])
def get_cp_detail(cp_id):
    """Endpoint para obtener detalle de un CP específico"""
    try:
        cp = db.obtener_cp(cp_id)

        if not cp:
            return jsonify({'status': 'error', 'mensaje': 'CP no encontrado'}), 404

        # Obtener suministro activo si existe
        suministro = db.obtener_suministro_activo(cp_id)

        cp_data = {
            'id': cp['id'],
            'estado': cp['estado'],
            'fecha_registro': cp['fecha_registro'].isoformat() if cp['fecha_registro'] else None,
            'latitud': float(cp['latitud']) if cp.get('latitud') else None,
            'longitud': float(cp['longitud']) if cp.get('longitud') else None,
            'estado_meteorologico': cp.get('estado_meteorologico'),
            'alerta_meteorologica': bool(cp.get('alerta_meteorologica', False)),
            'suministro_activo': None
        }

        if suministro:
            cp_data['suministro_activo'] = {
                'id': suministro['id'],
                'conductor_id': suministro['conductor_id'],
                'fecha_inicio': suministro['fecha_inicio'].isoformat() if suministro['fecha_inicio'] else None,
                'consumo_kwh': float(suministro['consumo_kwh']),
                'importe_total': float(suministro['importe_total'])
            }

        return jsonify({
            'status': 'ok',
            'cp': cp_data
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)}), 500


@app.route('/api/suministros', methods=['GET'])
def get_suministros():
    """Endpoint para obtener suministros activos"""
    try:
        suministros = db.obtener_suministros_activos()

        suministros_data = []
        for s in suministros:
            suministros_data.append({
                'id': s['id'],
                'conductor_id': s['conductor_id'],
                'cp_id': s['cp_id'],
                'fecha_inicio': s['fecha_inicio'].isoformat() if s['fecha_inicio'] else None,
                'consumo_kwh': float(s['consumo_kwh']),
                'importe_total': float(s['importe_total']),
                'estado': s['estado']
            })

        return jsonify({
            'status': 'ok',
            'suministros': suministros_data
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)}), 500


@app.route('/api/auditoria', methods=['GET'])
def get_auditoria():
    """Endpoint para obtener registros de auditoría"""
    try:
        modulo = request.args.get('modulo', None)
        limit = int(request.args.get('limit', 100))

        registros = db.obtener_auditoria(modulo, limit)

        registros_data = []
        for r in registros:
            registros_data.append({
                'id': r['id'],
                'timestamp': r['timestamp'].isoformat() if r['timestamp'] else None,
                'ip_origen': r['ip_origen'],
                'modulo': r['modulo'],
                'accion': r['accion'],
                'parametros': r['parametros'],
                'resultado': r['resultado'],
                'detalle': r['detalle']
            })

        return jsonify({
            'status': 'ok',
            'registros': registros_data
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)}), 500


# === ENDPOINTS PARA EV_W (Alertas Meteorológicas) ===

@app.route('/api/weather/alert', methods=['POST'])
def receive_weather_alert():
    """Endpoint para recibir alertas meteorológicas de EV_W"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'status': 'error', 'mensaje': 'No se recibieron datos'}), 400

        cp_id = data.get('cp_id')
        estado_meteorologico = data.get('estado')
        alerta = data.get('alerta', False)

        if not cp_id:
            return jsonify({'status': 'error', 'mensaje': 'cp_id requerido'}), 400

        # Actualizar estado meteorológico en BD
        db.actualizar_clima_cp(cp_id, estado_meteorologico, alerta)

        # Registrar en auditoría
        db.registrar_auditoria(
            ip_origen=request.remote_addr,
            modulo='EV_W',
            accion='alerta_meteorologica',
            parametros=f'{{"cp_id": "{cp_id}", "estado": "{estado_meteorologico}", "alerta": {alerta}}}',
            resultado='exito',
            detalle=f'Alerta meteorológica recibida para {cp_id}'
        )

        return jsonify({
            'status': 'ok',
            'mensaje': f'Alerta procesada para {cp_id}'
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)}), 500


@app.route('/api/weather/alerts', methods=['GET'])
def get_weather_alerts():
    """Endpoint para obtener CPs con alertas meteorológicas activas"""
    try:
        cps_alerta = db.obtener_cps_con_alerta_meteorologica()

        alertas_data = []
        for cp in cps_alerta:
            alertas_data.append({
                'cp_id': cp['id'],
                'estado': cp['estado'],
                'estado_meteorologico': cp.get('estado_meteorologico'),
                'latitud': float(cp['latitud']) if cp.get('latitud') else None,
                'longitud': float(cp['longitud']) if cp.get('longitud') else None
            })

        return jsonify({
            'status': 'ok',
            'alertas': alertas_data
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)}), 500


# === HEALTH CHECK ===

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que la API está funcionando"""
    return jsonify({
        'status': 'ok',
        'servicio': 'API_Central',
        'version': '2.0'
    }), 200


def inicializar_db(db_host, db_port):
    """Inicializa la conexión a la base de datos"""
    global db
    db = Database(
        host=db_host,
        port=db_port,
        user='evuser',
        password='evpass123',
        database='evcharging_db'
    )

    if not db.conectar():
        print("[ERROR] No se pudo conectar a la base de datos")
        return False

    print("[OK] API_Central conectada a la base de datos")
    return True


def main():
    if len(sys.argv) < 2:
        print("Uso: python api_server.py <puerto> [db_host:db_port]")
        print("Ejemplo: python api_server.py 8000 localhost:3306")
        sys.exit(1)

    puerto = int(sys.argv[1])

    db_host = 'localhost'
    db_port = 3306

    if len(sys.argv) >= 3:
        db_parts = sys.argv[2].split(':')
        db_host = db_parts[0]
        if len(db_parts) > 1:
            db_port = int(db_parts[1])

    print("\n" + "=" * 60)
    print("API_Central - API REST para Sistema de Gestión de Red de Carga")
    print("=" * 60 + "\n")

    if not inicializar_db(db_host, db_port):
        sys.exit(1)

    print(f"\n[OK] Iniciando servidor API en puerto {puerto}...")
    print(f"[INFO] Endpoints disponibles:")
    print(f"  GET  /health - Health check")
    print(f"  GET  /api/status - Estado general del sistema")
    print(f"  GET  /api/cps - Lista de todos los CPs")
    print(f"  GET  /api/cps/<cp_id> - Detalle de un CP")
    print(f"  GET  /api/suministros - Suministros activos")
    print(f"  GET  /api/auditoria - Registros de auditoría")
    print(f"  POST /api/weather/alert - Recibir alerta meteorológica")
    print(f"  GET  /api/weather/alerts - CPs con alertas activas")
    print("\n" + "=" * 60 + "\n")

    app.run(host='0.0.0.0', port=puerto, debug=False)


if __name__ == '__main__':
    main()