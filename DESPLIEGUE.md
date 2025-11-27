# Guía de Despliegue Completo - EV Charging System

Esta guía te llevará paso a paso desde cero hasta tener todo el sistema funcionando.

---

## 📋 Requisitos Previos

Antes de empezar, asegúrate de tener instalado:

- **Docker Desktop** (para MariaDB y Kafka)
- **Python 3.8+**
- **Git** (opcional, si vas a clonar el repo)
- **Navegador web** (Chrome, Firefox, Edge)

---

## 🚀 Paso 1: Iniciar Infraestructura Docker

### 1.1 Verificar que Docker está corriendo

```bash
# Abrir Docker Desktop primero (icono de escritorio)
# O ejecutar este comando para verificar:
docker --version
```

Deberías ver algo como: `Docker version 24.x.x`

### 1.2 Iniciar MariaDB

```bash
# Ir al directorio del proyecto
cd c:\Users\izanr\Desktop\sd-prac1

# Iniciar contenedor de MariaDB
docker run -d --name mariadb ^
  -e MYSQL_ROOT_PASSWORD=rootpass ^
  -e MYSQL_DATABASE=evcharging_db ^
  -e MYSQL_USER=evuser ^
  -e MYSQL_PASSWORD=evpass123 ^
  -p 3306:3306 ^
  mariadb:10.11
```

**Verificar que está corriendo:**
```bash
docker ps
# Deberías ver mariadb en la lista
```

### 1.3 Crear las tablas en MariaDB

```bash
# Ejecutar el script de inicialización
docker exec -i mariadb mysql -uroot -prootpass < init-db\init-query.sql
```

**Verificar que las tablas se crearon:**
```bash
docker exec -it mariadb mysql -uevuser -pevpass123 evcharging_db -e "SHOW TABLES;"
```

Deberías ver:
```
+---------------------------+
| Tables_in_evcharging_db   |
+---------------------------+
| auditoria                 |
| charging_points           |
| conductores               |
| suministros               |
+---------------------------+
```

### 1.4 Iniciar Kafka y Zookeeper

```bash
# Crear red de Docker para Kafka
docker network create kafka-network

# Iniciar Zookeeper
docker run -d --name zookeeper ^
  --network kafka-network ^
  -p 2181:2181 ^
  -e ZOOKEEPER_CLIENT_PORT=2181 ^
  confluentinc/cp-zookeeper:latest

# Esperar 10 segundos
timeout /t 10

# Iniciar Kafka
docker run -d --name kafka ^
  --network kafka-network ^
  -p 9092:9092 ^
  -e KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 ^
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 ^
  -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 ^
  confluentinc/cp-kafka:latest
```

**Verificar que Kafka está corriendo:**
```bash
docker ps
# Deberías ver: mariadb, zookeeper, kafka
```

---

## 📦 Paso 2: Instalar Dependencias Python

### 2.1 Instalar dependencias generales

```bash
# En el directorio raíz del proyecto
cd c:\Users\izanr\Desktop\sd-prac1

pip install -r requirements.txt
```

Esto instalará:
- `kafka-python` - Para Kafka
- `pymysql` - Para MariaDB
- `cryptography` - Para cifrado AES
- `DBUtils` - Para pool de conexiones

### 2.2 Instalar dependencias de API_Central

```bash
cd API_Central
pip install -r requirements.txt
cd ..
```

Esto instalará:
- `Flask` - Framework web
- `flask-cors` - Para permitir peticiones desde el frontend

---

## 🎯 Paso 3: Iniciar Componentes del Sistema

### 3.1 Iniciar EV_Central (Terminal 1)

```bash
# Abrir una nueva terminal (PowerShell o CMD)
cd c:\Users\izanr\Desktop\sd-prac1\EV_Central

# Ejecutar la central
python main.py 5000 localhost:9092 localhost:3306
```

**Deberías ver:**
```
============================================================
EV_CENTRAL - Sistema de Gestion de Red de Carga
============================================================

[OK] Connection pool creado para BD evcharging_db
[OK] Productor Kafka inicializado en localhost:9092
[OK] Consumidor Kafka inicializado
[OK] Servidor Socket escuchando en puerto 5000
[OK] Todos los topics ya existen
[OK] Consumidor Kafka ejecutandose en segundo plano

============================================================
SISTEMA INICIADO CORRECTAMENTE
============================================================

Abriendo panel de monitorizacion GUI...
```

**Dejar esta terminal abierta** - La GUI de EV_Central se abrirá automáticamente.

### 3.2 Iniciar API_Central (Terminal 2)

```bash
# Abrir una SEGUNDA terminal
cd c:\Users\izanr\Desktop\sd-prac1\API_Central

# Ejecutar la API REST
python api_server.py 8000 localhost:3306
```

**Deberías ver:**
```
============================================================
API_Central - API REST para Sistema de Gestión de Red de Carga
============================================================

[OK] API_Central conectada a la base de datos
[OK] Iniciando servidor API en puerto 8000...
[INFO] Endpoints disponibles:
  GET  /health - Health check
  GET  /api/status - Estado general del sistema
  GET  /api/cps - Lista de todos los CPs
  ...

 * Running on http://0.0.0.0:8000
```

**Dejar esta terminal abierta**.

### 3.3 Verificar que API funciona

```bash
# En una tercera terminal, ejecutar:
curl http://localhost:8000/health

# Deberías ver:
# {"servicio":"API_Central","status":"ok","version":"2.0"}
```

O abrir en navegador: http://localhost:8000/health

---

## 🌐 Paso 4: Abrir Frontend Web

### 4.1 Abrir el archivo HTML

```bash
# Opción 1: Doble clic en el archivo
# Ir a: c:\Users\izanr\Desktop\sd-prac1\FRONT\index.html
# Doble clic → Se abre en navegador predeterminado

# Opción 2: Desde terminal
start FRONT\index.html

# Opción 3: Servidor HTTP (opcional)
cd FRONT
python -m http.server 8080
# Luego abrir: http://localhost:8080
```

**Deberías ver:**
- Dashboard con tarjetas de estadísticas
- Tabla de CPs vacía (o con datos si ya has creado CPs)
- Panel de suministros
- Registro de auditoría

El frontend se actualizará automáticamente cada 3 segundos.

---

## 🔌 Paso 5: Crear y Conectar Puntos de Carga (CPs)

### 5.1 Crear CPs con el script batch (Terminal 3)

```bash
cd c:\Users\izanr\Desktop\sd-prac1

# Crear 3 CPs en localhost
create_cps.bat 3 localhost

# O especificar IP de la central
create_cps.bat 3 192.168.1.100
```

Esto abrirá 6 ventanas:
- 3 ventanas de **EV_CP_E** (Engines) en puertos 5050, 5051, 5052
- 3 ventanas de **EV_CP_M** (Monitors) con IDs CP001, CP002, CP003

**En la terminal de EV_Central verás:**
```
[AUTENTICACIÓN] CP CP001 conectándose...
[REGISTRO] Nuevo CP: CP001
[CRYPTO] Nueva clave generada para CP001
[CRYPTO] Clave de cifrado generada para CP001
[OK] Monitor de CP CP001 autenticado
```

### 5.2 Verificar en Frontend

Recargar el frontend (F5) y deberías ver:
- Total CPs: 3
- Los 3 CPs listados en la tabla
- Estado: "activado" (en verde)

### 5.3 Verificar en API

```bash
curl http://localhost:8000/api/cps
```

Deberías ver JSON con los 3 CPs y sus claves de cifrado generadas.

---

## 👤 Paso 6: Crear Conductores (Drivers)

### 6.1 Crear conductores con el script batch (Terminal 4)

```bash
cd c:\Users\izanr\Desktop\sd-prac1

# Crear 2 conductores
create_drivers.bat 2 localhost
```

Esto abrirá 2 ventanas de **EV_Driver** con IDs DRV001 y DRV002.

**En la terminal de EV_Central verás:**
```
[REGISTRO] Conductor DRV001 conectado
```

**En la auditoría del frontend verás:**
- Acción: "registro_conductor"
- Módulo: "EV_Central"
- Resultado: "exito"

---

## 🔋 Paso 7: Realizar un Suministro Completo

### 7.1 En la ventana del Driver (DRV001)

```
=== Cliente EV Driver: DRV001 ===

Comandos disponibles:
  listar           - Ver CPs disponibles
  solicitar <CP>   - Solicitar suministro
  ver              - Ver estado del suministro
  salir            - Desconectar

> listar
```

**Verás:**
```
[LISTADO] Recibida lista de CPs:
  - CP001 (activado)
  - CP002 (activado)
  - CP003 (activado)
```

### 7.2 Solicitar suministro

```
> solicitar CP001
```

**En el Driver verás:**
```
[SOLICITUD ENVIADA] Esperando respuesta de la central...
[AUTORIZACION] Suministro autorizado en CP001
[INICIO] Suministro iniciado. ID: 1
```

**En el frontend verás:**
- Suministros Activos: 1
- CP001 estado: "suministrando" (azul)
- Nueva entrada en auditoría: "inicio_suministro"

### 7.3 Ver telemetría en tiempo real

**En el Driver:**
```
> ver
```

Verás actualizaciones cada segundo:
```
[TELEMETRIA] Consumo actual: 1.245 kWh | Importe: 0.62 EUR
[TELEMETRIA] Consumo actual: 2.456 kWh | Importe: 1.23 EUR
...
```

**En el frontend:**
- La tabla de "Suministros Activos" se actualiza automáticamente
- Consumo e importe aumentan en tiempo real

### 7.4 Finalizar suministro

**En la ventana del Driver:**
```
Presiona Ctrl+C para detener el suministro
```

**Verás:**
```
[FIN] Suministro finalizado
[TICKET RECIBIDO]
=============================================
           TICKET DE SUMINISTRO
=============================================
  CP:              CP001
  Suministro ID:   1
  Consumo total:   15.234 kWh
  Importe total:   7.62 EUR
  Fecha:           2025-01-15 14:30:45
=============================================
```

**En el frontend:**
- CP001 vuelve a estado "activado"
- Suministros Activos: 0
- Auditoría: "fin_suministro"

---

## 📊 Paso 8: Verificar Auditoría

### 8.1 En el Frontend

Scrollear a la sección "Registro de Auditoría (Últimos 50)".

Deberías ver:
```
Timestamp              | Módulo     | Acción                | IP         | Resultado
2025-01-15 14:30:45   | EV_Central | fin_suministro        | localhost  | exito
2025-01-15 14:25:30   | EV_Central | inicio_suministro     | localhost  | exito
2025-01-15 14:25:00   | EV_Central | registro_conductor    | localhost  | exito
2025-01-15 14:24:50   | EV_Central | generacion_clave      | localhost  | exito
2025-01-15 14:24:45   | EV_Central | autenticacion_cp      | localhost  | exito
```

### 8.2 En la API

```bash
curl http://localhost:8000/api/auditoria?limit=10
```

### 8.3 En la Base de Datos

```bash
docker exec -it mariadb mysql -uevuser -pevpass123 evcharging_db

# En MySQL:
SELECT timestamp, modulo, accion, resultado, detalle
FROM auditoria
ORDER BY timestamp DESC
LIMIT 10;
```

---

## 🌦️ Paso 9: Probar Alertas Meteorológicas

### 9.1 Simular alerta de EV_W

```bash
# Desde PowerShell o CMD
curl -X POST http://localhost:8000/api/weather/alert ^
  -H "Content-Type: application/json" ^
  -d "{\"cp_id\": \"CP001\", \"estado\": \"Tormenta fuerte\", \"alerta\": true}"
```

**Respuesta:**
```json
{"mensaje":"Alerta procesada para CP001","status":"ok"}
```

### 9.2 Verificar en Frontend

Recargar frontend (o esperar 3 segundos):

**En la sección "Alertas Meteorológicas":**
```
⚠️ CP001
Estado: suministrando
Clima: Tormenta fuerte
Ubicación: No disponible
```

La tarjeta aparecerá con fondo rojo.

**En "Estado General del Sistema":**
- Alertas Clima: 1

### 9.3 Consultar CPs con alertas

```bash
curl http://localhost:8000/api/weather/alerts
```

---

## 🛑 Paso 10: Detener Todo

### 10.1 Detener componentes Python

**En cada terminal abierta:**
- Terminal EV_Central: `Ctrl+C`
- Terminal API_Central: `Ctrl+C`
- Ventanas de CPs: `Ctrl+C` en cada una
- Ventanas de Drivers: `Ctrl+C` o escribir `salir`

### 10.2 Detener Docker

```bash
# Detener contenedores
docker stop mariadb kafka zookeeper

# Eliminar contenedores (opcional, si quieres empezar limpio)
docker rm mariadb kafka zookeeper

# Eliminar red (opcional)
docker network rm kafka-network
```

---

## 🔄 Reiniciar Todo Después

Si ya tienes Docker corriendo y solo quieres reiniciar los componentes:

```bash
# 1. Iniciar Docker containers
docker start mariadb zookeeper kafka

# 2. Esperar 10 segundos
timeout /t 10

# 3. Terminal 1: Central
cd c:\Users\izanr\Desktop\sd-prac1\EV_Central
python main.py 5000 localhost:9092 localhost:3306

# 4. Terminal 2: API
cd c:\Users\izanr\Desktop\sd-prac1\API_Central
python api_server.py 8000 localhost:3306

# 5. Abrir Frontend
start FRONT\index.html

# 6. Crear CPs (Terminal 3)
cd c:\Users\izanr\Desktop\sd-prac1
create_cps.bat 3 localhost

# 7. Crear Drivers (Terminal 4)
create_drivers.bat 2 localhost
```

---

## 🐛 Solución de Problemas

### Error: "Cannot connect to MariaDB"

**Solución:**
```bash
# Verificar que MariaDB está corriendo
docker ps

# Si no está, iniciarlo
docker start mariadb

# Verificar logs
docker logs mariadb
```

### Error: "Kafka connection failed"

**Solución:**
```bash
# Iniciar Zookeeper primero
docker start zookeeper

# Esperar 10 segundos
timeout /t 10

# Luego Kafka
docker start kafka

# Verificar logs
docker logs kafka
```

### Error: Frontend no muestra datos

**Solución:**
1. Verificar que API_Central está corriendo: http://localhost:8000/health
2. Abrir consola del navegador (F12) y revisar errores
3. Verificar que `API_BASE_URL` en `app.js` es correcto: `http://localhost:8000/api`

### Error: "Module not found: cryptography"

**Solución:**
```bash
pip install cryptography
```

### Puerto 5000/8000/9092 ya en uso

**Solución:**
```bash
# Ver qué proceso usa el puerto (PowerShell)
netstat -ano | findstr :5000

# Matar proceso (reemplazar PID)
taskkill /PID <numero_pid> /F
```

---

## 📝 Resumen de Puertos

| Componente      | Puerto | URL                          |
|-----------------|--------|------------------------------|
| MariaDB         | 3306   | localhost:3306               |
| Kafka           | 9092   | localhost:9092               |
| Zookeeper       | 2181   | localhost:2181               |
| EV_Central      | 5000   | localhost:5000 (socket)      |
| API_Central     | 8000   | http://localhost:8000        |
| Frontend        | -      | FRONT/index.html (archivo)   |
| CP Engines      | 5050+  | localhost:5050, 5051, 5052   |

---

## ✅ Checklist de Verificación

- [ ] Docker Desktop abierto y corriendo
- [ ] MariaDB iniciado: `docker ps | findstr mariadb`
- [ ] Kafka iniciado: `docker ps | findstr kafka`
- [ ] Tablas creadas: `docker exec -it mariadb mysql -uevuser -pevpass123 evcharging_db -e "SHOW TABLES;"`
- [ ] EV_Central corriendo: Ver "SISTEMA INICIADO CORRECTAMENTE"
- [ ] API_Central corriendo: `curl http://localhost:8000/health`
- [ ] Frontend abierto en navegador
- [ ] CPs creados y conectados: Ver en frontend "Total CPs: 3"
- [ ] Drivers creados: Ver en auditoría "registro_conductor"
- [ ] Suministro funcional: Solicitar en driver y ver en frontend

---

## 🎉 ¡Sistema Completo Funcionando!

Si has llegado aquí, deberías tener:
✅ 3 CPs conectados con claves de cifrado
✅ 2 Conductores registrados
✅ API REST respondiendo
✅ Frontend mostrando datos en tiempo real
✅ Auditoría registrando todos los eventos
✅ Sistema de suministros completo operativo

**Prueba realizar un suministro completo y observa:**
- Dashboard de frontend actualizándose
- Auditoría capturando cada evento
- Telemetría en tiempo real
- Ticket generado al finalizar