# EV Charging System - Release 2

## Nuevas Funcionalidades Implementadas

### 1. Extensión de Base de Datos

#### Nuevas Tablas
- **auditoria**: Tabla para registro de eventos del sistema
  - Campos: timestamp, ip_origen, modulo, accion, parametros, resultado, detalle
  - Índices en timestamp, modulo y accion para consultas eficientes

#### Nuevos Campos en charging_points
- **clave_cifrado**: Clave simétrica única para cifrado de mensajes
- **fecha_generacion_clave**: Timestamp de generación de clave
- **latitud/longitud**: Coordenadas GPS del CP
- **estado_meteorologico**: Estado del clima actual
- **alerta_meteorologica**: Flag de alerta activa

### 2. API_Central (Nuevo Módulo)

Servidor REST API implementado con Flask que expone endpoints para consulta y gestión del sistema.

#### Endpoints Implementados

**Estado del Sistema:**
- `GET /health` - Health check de la API
- `GET /api/status` - Estado general con estadísticas de CPs y suministros

**Puntos de Carga:**
- `GET /api/cps` - Lista completa de CPs con ubicación y estado meteorológico
- `GET /api/cps/<cp_id>` - Detalle de un CP específico incluyendo suministro activo

**Suministros:**
- `GET /api/suministros` - Lista de suministros activos en el sistema

**Auditoría:**
- `GET /api/auditoria?modulo=X&limit=N` - Registros de auditoría filtrados

**Meteorología (Integración con EV_W):**
- `POST /api/weather/alert` - Recibe alertas meteorológicas de EV_W
- `GET /api/weather/alerts` - CPs con alertas meteorológicas activas

#### Ejecución
```bash
cd API_Central
pip install -r requirements.txt
python api_server.py 8000 localhost:3306
```

### 3. FRONT (Nuevo Módulo)

Interfaz web de monitorización que consume la API_Central.

#### Características
- Dashboard con estadísticas en tiempo real
- Tabla de CPs con estado, clima y ubicación
- Visualización de suministros activos
- Panel de alertas meteorológicas
- Registro de auditoría en tiempo real
- Actualización automática cada 3 segundos

#### Ejecución
```bash
cd FRONT
# Abrir index.html en navegador
# Configurar API_BASE_URL en app.js si es necesario
```

### 4. Sistema de Auditoría en EV_Central

Nuevo módulo `auditoria.py` que registra automáticamente todos los eventos críticos:

- Autenticación de CPs (exitosa/fallida)
- Inicio y finalización de suministros
- Averías y recuperaciones de CPs
- Desconexiones de monitores
- Registro de conductores
- Generación y restauración de claves de cifrado
- Alertas meteorológicas
- Comandos enviados a CPs

Todos los eventos incluyen:
- Timestamp automático
- IP de origen
- Módulo que generó el evento
- Acción realizada
- Parámetros (en JSON)
- Resultado (éxito/error)
- Detalle descriptivo

### 5. Sistema de Cifrado (EV_Central)

Nuevo módulo `crypto_manager.py` con cifrado simétrico AES mediante Fernet.

#### Características
- Clave única por CP generada automáticamente
- Cifrado/descifrado de mensajes JSON
- Cache de claves en memoria para rendimiento
- Persistencia en base de datos
- Restauración de claves al reconectar
- Auditoría de operaciones criptográficas

#### Integración
- Generación automática de clave al registrar nuevo CP
- Restauración de clave al autenticar CP existente
- Métodos `cifrar_mensaje()` y `descifrar_mensaje()` disponibles en LogicaNegocio

### 6. Mejoras en Seguridad

- **Autenticación robusta**: Cada CP tiene credenciales únicas (ID + clave de cifrado)
- **Canal seguro**: Mensajes cifrados con AES-128
- **Trazabilidad completa**: Todos los eventos registrados en auditoría
- **Restauración de claves**: Sistema de backup y recuperación de claves

## Dependencias Nuevas

### EV_Central
```bash
pip install cryptography
```

### API_Central
```bash
pip install Flask flask-cors
```

## Arquitectura Release 2

```
┌─────────────┐
│   EV_W      │ (Externo - envía alertas meteorológicas)
└──────┬──────┘
       │ POST /api/weather/alert
       ▼
┌─────────────────────────────────────────────────┐
│              API_Central (Puerto 8000)          │
│  - REST API Flask                               │
│  - Endpoints de consulta                        │
│  - Recepción de alertas meteorológicas         │
│  - CORS habilitado para FRONT                  │
└────────────┬────────────────────────────────────┘
             │
             │ Consultas SQL
             ▼
┌─────────────────────────────────────────────────┐
│           MariaDB (Puerto 3306)                 │
│  Tablas:                                        │
│  - charging_points (+ crypto & weather fields)  │
│  - suministros                                  │
│  - conductores                                  │
│  - auditoria (NUEVA)                            │
└────────────┬────────────────────────────────────┘
             │
             │ Pool de conexiones
             ▼
┌─────────────────────────────────────────────────┐
│          EV_Central (Puerto 5000)               │
│  Módulos nuevos:                                │
│  - auditoria.py: Sistema de logging             │
│  - crypto_manager.py: Cifrado AES               │
│  Extensiones en logica_negocio.py:             │
│  - Integración con auditoría                    │
│  - Gestión de claves de cifrado                 │
│  - Registro de eventos de seguridad            │
└─────────────────────────────────────────────────┘
             ▲
             │ Socket TCP (auth + cifrado)
             │
┌─────────────────────────────────────────────────┐
│          EV_CP_M (Monitors)                     │
│  - Autenticación con Central                    │
│  - Canal potencialmente cifrado                 │
└─────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────┐
│              FRONT (Web UI)                     │
│  - HTML/CSS/JavaScript                          │
│  - Consume API_Central vía fetch()             │
│  - Auto-refresh cada 3 segundos                │
│  - Visualización de alertas meteorológicas     │
└─────────────────────────────────────────────────┘
```

## Guía de Despliegue Release 2

### 1. Actualizar Base de Datos
```bash
docker exec -i mariadb mysql -uroot -prootpass < init-db/init-query.sql
```

### 2. Iniciar EV_Central (con nuevos módulos)
```bash
cd EV_Central
pip install cryptography  # Nueva dependencia
python main.py 5000 localhost:9092 localhost:3306
```

### 3. Iniciar API_Central
```bash
cd API_Central
pip install -r requirements.txt
python api_server.py 8000 localhost:3306
```

### 4. Abrir Frontend
```bash
cd FRONT
# Abrir index.html en navegador Chrome/Firefox
# La página se conectará automáticamente a http://localhost:8000
```

### 5. Verificar Funcionamiento
- Health check API: `curl http://localhost:8000/health`
- Estado del sistema: `curl http://localhost:8000/api/status`
- Frontend: Abrir `http://localhost:8000/index.html` o archivo local

## Notas de Seguridad

### Claves de Cifrado
- Las claves se generan automáticamente usando `Fernet.generate_key()`
- Se almacenan en base64 en la columna `charging_points.clave_cifrado`
- **IMPORTANTE**: En producción, considerar cifrar las claves en BD con clave maestra

### Auditoría
- Todos los eventos se registran automáticamente
- La IP de origen se captura para trazabilidad
- Los parámetros se almacenan en JSON para análisis posterior

### API REST
- CORS está habilitado para desarrollo
- En producción, configurar `CORS(app, origins=['https://tudominio.com'])`
- Considerar añadir autenticación JWT para endpoints sensibles

## Integración con EV_W (Futuro)

El sistema está preparado para recibir alertas meteorológicas de EV_W:

```bash
# Ejemplo de alerta meteorológica
curl -X POST http://localhost:8000/api/weather/alert \
  -H "Content-Type: application/json" \
  -d '{
    "cp_id": "CP001",
    "estado": "Tormenta fuerte",
    "alerta": true
  }'
```

EV_W debe enviar alertas a `POST /api/weather/alert` cuando detecte condiciones adversas.

## Testing

### Test de API
```bash
# Estado general
curl http://localhost:8000/api/status

# Lista de CPs
curl http://localhost:8000/api/cps

# Auditoría
curl http://localhost:8000/api/auditoria?limit=10
```

### Test de Cifrado
```python
from crypto_manager import CryptoManager
from database import Database

db = Database('localhost', 3306, 'evuser', 'evpass123', 'evcharging_db')
db.conectar()

crypto = CryptoManager(db)

# Generar clave para CP001
clave = crypto.generar_clave_para_cp('CP001')
print(f"Clave generada: {clave}")

# Cifrar mensaje
mensaje = {'tipo': 'TEST', 'dato': 'Hola CP001'}
cifrado = crypto.cifrar_mensaje('CP001', mensaje)
print(f"Mensaje cifrado: {cifrado}")

# Descifrar
descifrado = crypto.descifrar_mensaje('CP001', cifrado)
print(f"Mensaje descifrado: {descifrado}")
```

## Changelog Release 2

### Añadido
- Módulo API_Central con 8 endpoints REST
- Frontend web con dashboard de monitorización
- Sistema de auditoría completo
- Cifrado simétrico AES para comunicación con CPs
- Gestión de claves criptográficas
- Integración con alertas meteorológicas
- Campos de ubicación GPS en CPs

### Modificado
- `database.py`: 9 nuevos métodos para crypto, weather y auditoría
- `logica_negocio.py`: Integración con auditoría y crypto
- Schema BD: Tabla `auditoria` y nuevos campos en `charging_points`

### Seguridad
- Claves únicas por CP
- Registro de todos los eventos críticos
- Trazabilidad completa de acciones

## Próximos Pasos (Release 3)

1. Implementar cifrado real en comunicación Monitor-Central
2. Integrar EV_W real con OpenWeather API
3. Añadir autenticación JWT en API_Central
4. Dashboard de administración en FRONT
5. Exportación de auditoría a CSV/PDF
6. Alertas push para eventos críticos