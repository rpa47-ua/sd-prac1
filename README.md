# EVCharging - Sistema Central de Gestión

Práctica de Sistemas Distribuidos - Curso 2025/26
Izan Ruzafa y Ramón Pastor

## Descripción

Sistema de gestión centralizado para una red de puntos de recarga de vehículos eléctricos.

**Tecnologías:**
- Python 3
- Apache Kafka (streaming de eventos)
- MariaDB (base de datos)
- Sockets TCP (comunicación con CPs)
- Tkinter (interfaz gráfica)

## Estructura del Proyecto

```
sd-prac1/
├── EV_Central/
│   ├── EV_Central.py
│   ├── panel_gui.py
│   ├── database.py
│   ├── kafka_handler.py
│   ├── servidor_socket.py
│   └── logica_negocio.py
├── EV_CP_E/
│   ├── EV_CP_E.py
│   ├── gui.py
│   └── engine_state_*.json
├── EV_CP_M/
│   ├── EV_CP_M.py
│   ├── gui.py
├── EV_DRIVER/
│   ├── EV_Driver.py
│   ├── gui.py
│   └── drv*.txt
├── init-db/
│   └── init-query.sql
├── compose.yml
├── requirements.txt
├── crear_topics.bat
├── create_cps.bat
├── create_drivers.bat
├── test_conexiones.py
└── README.md
```

## 5. Guía de Despliegue

Para la correcta puesta en marcha del sistema desarrollado, es necesario seguir una serie de pasos que aseguren la instalación de las dependencias y la correcta configuración de los distintos componentes.

### 5.1. Instalación de dependencias

En primer lugar, se deben instalar los requerimientos necesarios para la ejecución del proyecto. Desde el repositorio principal, se ejecuta el siguiente comando:

```bash
pip install -r requirements.txt
```

Este proceso instalará todas las librerías necesarias tanto de Kafka como de base de datos para el funcionamiento de los distintos módulos.

### 5.2. Docker

A continuación, se deben desplegar los servicios base (Kafka, base de datos, etc.) utilizando Docker. Para ello, se recomienda abrir la aplicación Docker Desktop y, desde el mismo directorio del repositorio, ejecutar el siguiente comando:

```bash
docker-compose up -d
```

**Importante:** Antes de realizar este paso, es necesario modificar el archivo `docker-compose.yml`, concretamente en la línea 11, sustituyendo la dirección `localhost` por la dirección IP del equipo en el que se ejecutará el componente Central. De este modo, se garantiza que el resto de módulos del sistema puedan establecer conexión con dicho equipo y comunicarse correctamente durante la ejecución.

No obstante, si todos los componentes se despliegan en una única máquina, puede mantenerse la configuración por defecto con `localhost`, sin necesidad de realizar cambios adicionales.

Esto levanta:
- Kafka en puerto `9092`
- Zookeeper en puerto `2181`
- MariaDB en puerto `3306`

### 5.3. Ejecución de la Central

Una vez levantados los servicios, se procede a iniciar el módulo Central. Para ello, desde un terminal ubicado en el directorio `EV_Central`, se ejecuta el siguiente comando:

```bash
python main.py <puerto_socket> [ip_kafka:kafka_puerto] [ip_dbhost:db_puerto]
```

**Ejemplo:**

```bash
python main.py 5000 localhost:9092 localhost:3306
```

**Parámetros:**
- `puerto_socket`: Puerto donde la Central escuchará conexiones de Monitores (default: `5000`)
- `ip_kafka:kafka_puerto`: Dirección y puerto del servidor Kafka (default: `localhost:9092`)
- `ip_dbhost:db_puerto`: Dirección y puerto de la base de datos (default: `localhost:3306`)

**Puertos por defecto:**
- Kafka: `9092`
- Base de datos: `3306`

En caso de que la ejecución se realice en distintos equipos, debe sustituirse `localhost` por la dirección IP correspondiente.

Al ejecutar la Central, se abrirá una interfaz gráfica que muestra:
- Estado de todos los Charging Points
- Estadísticas en tiempo real
- Controles para parar/reanudar CPs

### 5.4. Despliegue de los módulos CP

Una vez en funcionamiento la Central, se pueden crear los distintos CPs mediante el siguiente script ubicado en el directorio principal:

```bash
create_cps.bat [cantidad] [numero_inicial] [puerto_inicial] [ip_central]
```

**Ejemplo de ejecución:**

```bash
create_cps.bat 5 1 5050 localhost
```

**Parámetros:**
- `cantidad`: Número de CPs a crear (default: `5`)
- `numero_inicial`: Primer número del CP (default: `1`)
- `puerto_inicial`: Puerto inicial para los Engines (default: `5050`)
- `ip_central`: Dirección IP del equipo donde se ejecuta la Central (default: `localhost`)

El parámetro `ip_central` debe indicar la dirección IP del equipo en el que se encuentra desplegado el componente Central, ya que será el punto de referencia para la comunicación del resto de módulos del sistema. En caso de que todos los componentes se ejecuten en un mismo equipo, puede conservarse el valor por defecto `localhost`, sin que ello afecte al funcionamiento general.

**Ejemplos:**
```bash
create_cps.bat 5 1 5050 localhost          # Crea CP01 a CP05, puertos 5050-5054
create_cps.bat 3 11 6000 192.168.1.10      # Crea CP11 a CP13, puertos 6000-6002
create_cps.bat 10 1 5050                   # Usa localhost por defecto
```

Este script lanza automáticamente:
1. Los Engines de cada CP (conectados a Kafka)
2. Los Monitores correspondientes (conectados al Engine local y a la Central)

### 5.5. Despliegue de los módulos Driver

Finalmente, se despliegan los Drivers del sistema ejecutando el siguiente script, también ubicado en el directorio principal:

```bash
create_drivers.bat [cantidad] [numero_inicial] [ip_central]
```

**Ejemplo:**

```bash
create_drivers.bat 5 1 localhost
```

**Parámetros:**
- `cantidad`: Número de Drivers a crear (default: `5`)
- `numero_inicial`: Primer número del Driver (default: `1`)
- `ip_central`: Dirección IP del equipo donde se ejecuta la Central (default: `localhost`)

Al igual que en el caso anterior, `ip_central` hace referencia a la dirección del equipo donde se ejecuta la Central.

**Ejemplos:**
```bash
create_drivers.bat 5 1 localhost           # Crea DRV001 a DRV005
create_drivers.bat 3 11 192.168.1.10       # Crea DRV011 a DRV013
create_drivers.bat 10 1                    # Usa localhost por defecto
```

## Configuración

**Base de datos:**
- Usuario: `evuser`
- Password: `evpass123`
- Database: `evcharging_db`
- Puerto: `3306`

**Kafka:**
- Bootstrap servers: `localhost:9092`

**Central:**
- Puerto socket: `5000`

## Orden de Arranque Recomendado

Para un correcto despliegue del sistema completo, seguir este orden:

1. **Levantar infraestructura con Docker** (`docker-compose up -d`)
2. **Ejecutar Central** (`python EV_Central/main.py 5000 localhost:9092 localhost:3306`)
3. **Crear CPs** (`create_cps.bat 5 1 5050 localhost`)
4. **Crear Drivers** (`create_drivers.bat 5 1 localhost`)

## Verificación del Sistema

Una vez desplegados todos los componentes, verificar:

- ✅ La interfaz gráfica de la Central muestra todos los CPs conectados
- ✅ Los CPs aparecen en estado "ACTIVADO" (verde)
- ✅ Los Drivers pueden solicitar suministros
- ✅ Los suministros se procesan correctamente y se emiten tickets

## Solución de Problemas Comunes

**Kafka no conecta:**
- Verificar que el contenedor de Kafka está corriendo: `docker ps`
- Comprobar que el puerto 9092 está accesible
- Revisar la IP configurada en `docker-compose.yml`

**Base de datos no se inicializa:**
- Verificar logs del contenedor: `docker logs sd-prac1-mariadb-1`
- Comprobar que el volumen `mariadb_data` existe
- Verificar que el script `init-query.sql` se ejecutó correctamente

**CPs no aparecen en la Central:**
- Verificar que la Central está escuchando en el puerto correcto (5000)
- Comprobar que la IP de la Central es accesible desde los Monitores
- Revisar logs de los Monitores para errores de conexión

**Drivers no reciben tickets:**
- Verificar que los Drivers están conectados a Kafka
- Comprobar que el topic `tickets` existe
- Revisar logs de la Central para errores en el envío de tickets