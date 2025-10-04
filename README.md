# EVCharging - Sistema Distribuido de Gestión de Puntos de Recarga

Práctica de Sistemas Distribuidos - Curso 2025/26

## 📋 Descripción

Sistema distribuido para la gestión de una red de puntos de recarga de vehículos eléctricos, implementado con:
- **Sockets TCP** para comunicación entre componentes
- **Apache Kafka** para streaming de eventos
- **MariaDB** como base de datos
- **Python 3** como lenguaje de desarrollo

## 🏗️ Arquitectura

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  EV_Driver  │────────▶│  EV_Central  │◀────────│   EV_CP     │
│ (Conductor) │  Kafka  │   (Central)  │ Socket  │ (Charging   │
│             │         │              │         │  Point)     │
└─────────────┘         └──────────────┘         └─────────────┘
                               │
                        ┌──────┴──────┐
                        │             │
                    ┌───▼───┐    ┌────▼────┐
                    │ Kafka │    │ MariaDB │
                    └───────┘    └─────────┘
```

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
cd sd-prac1
```

### 2. Instalar dependencias Python

```bash
pip install -r requirements.txt
```

### 3. Levantar infraestructura con Docker

```bash
docker-compose -f compose.yml up -d
```

Esto levanta:
- **Kafka** en `localhost:9092`
- **MariaDB** en `localhost:3306`
- **PHPMyAdmin** en `http://localhost:8080`

### 4. Verificar que los servicios están activos

```bash
docker-compose ps
```

## 📦 Componentes

### EV_Central (Módulo Central)

**Ubicación:** `EV_Central/`

**Ejecución:**
```bash
cd EV_Central
python main.py <puerto_socket> <kafka_broker> [db_host:db_port]
```

**Ejemplo:**
```bash
python main.py 5000 localhost:9092 localhost:3306
```

**Funcionalidades:**
- ✅ Servidor socket TCP para autenticación de CPs
- ✅ Consumidor/Productor Kafka para gestión de eventos
- ✅ Lógica de autorización de suministros
- ✅ Panel de monitorización en tiempo real
- ✅ Gestión de base de datos

### EV_CP (Charging Point)

**Ubicación:** `EV_CP/`

Consta de dos módulos:

#### EV_CP_M (Monitor)
```bash
python monitor.py <cp_id> <ubicacion> <central_ip:puerto> <kafka_broker>
```

#### EV_CP_E (Engine)
```bash
python engine.py <cp_id> <kafka_broker>
```

### EV_Driver (Aplicación Conductor)

**Ubicación:** `EV_Driver/`

```bash
python driver.py <conductor_id> <kafka_broker> [archivo_servicios]
```

**Ejemplo:**
```bash
python driver.py DRV001 localhost:9092
```

## 🔧 Configuración

### Base de Datos

- **Host:** localhost
- **Puerto:** 3306
- **Usuario:** evuser
- **Password:** evpass123
- **Base de datos:** evcharging_db

### Kafka

- **Bootstrap server:** localhost:9092
- **Topics utilizados:**
  - `solicitudes_suministro` - Solicitudes de conductores
  - `respuestas_conductor` - Respuestas de autorización
  - `comandos_cp` - Comandos a Charging Points
  - `telemetria_cp` - Telemetría en tiempo real
  - `fin_suministro` - Finalización de suministros
  - `averias` - Notificaciones de averías
  - `recuperacion_cp` - Recuperación de CPs
  - `tickets` - Tickets finales para conductores

## 📊 Base de Datos

### Tabla: conductores
```sql
id VARCHAR(50) PRIMARY KEY
nombre VARCHAR(100)
apellidos VARCHAR(150)
email VARCHAR(100)
fecha_registro TIMESTAMP
```

### Tabla: charging_points
```sql
id VARCHAR(50) PRIMARY KEY
ubicacion VARCHAR(250)
precio_kwh DECIMAL(6,3)
estado ENUM('desconectado', 'activado', 'parado', 'suministrando', 'averiado')
fecha_registro TIMESTAMP
```

### Tabla: suministros
```sql
id INT AUTO_INCREMENT PRIMARY KEY
conductor_id VARCHAR(50)
cp_id VARCHAR(50)
fecha_inicio TIMESTAMP
fecha_fin TIMESTAMP
consumo_kwh DECIMAL(8,3)
importe_total DECIMAL(10,2)
estado VARCHAR(20)
```

## 🎯 Flujo de Operación

1. **Inicio del sistema**
   - Levantar Docker Compose (Kafka + MariaDB)
   - Ejecutar EV_Central

2. **Registro de Charging Points**
   - Ejecutar EV_CP_M (se autentica vía socket)
   - Ejecutar EV_CP_E (queda en espera)

3. **Solicitud de suministro**
   - Ejecutar EV_Driver
   - Conductor solicita recarga en un CP
   - Central valida y autoriza
   - CP inicia suministro

4. **Durante el suministro**
   - CP envía telemetría cada segundo
   - Central actualiza BD y panel

5. **Finalización**
   - Conductor desenchufa (simular en CP)
   - Central genera ticket
   - CP vuelve a estado disponible

## 🧪 Pruebas

### Probar conexión a Kafka
```bash
python producer_kafka.py
python consumer_kafka.py
```

### Probar conexión a MariaDB
```bash
# Acceder a PHPMyAdmin
http://localhost:8080
User: evuser
Pass: evpass123
```

## 📝 Estados de los Charging Points

| Estado | Color | Descripción |
|--------|-------|-------------|
| `activado` | 🟢 Verde | Disponible para uso |
| `parado` | 🟠 Naranja | Fuera de servicio (manual) |
| `suministrando` | 🔵 Cyan | Suministrando energía |
| `averiado` | 🔴 Rojo | Avería detectada |
| `desconectado` | ⚪ Gris | No conectado a central |

## 🐛 Troubleshooting

### Kafka no se conecta
```bash
# Verificar que el contenedor está corriendo
docker ps | grep broker

# Ver logs
docker logs broker
```

### MariaDB no se conecta
```bash
# Verificar contenedor
docker ps | grep mariadb

# Reiniciar
docker-compose restart mariadb
```

### Error de módulos Python
```bash
pip install --upgrade -r requirements.txt
```

## 📚 Documentación Adicional

- [Apache Kafka](https://kafka.apache.org/documentation/)
- [Protocolo OCPP](https://www.openchargealliance.org/)
- [Python Socket Programming](https://docs.python.org/3/library/socket.html)

## �� Autores

Práctica de Sistemas Distribuidos - Universidad de Alicante

## 📄 Licencia

Proyecto académico - Curso 2025/26
