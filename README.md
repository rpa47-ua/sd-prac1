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

## Instalación

### 1. Instalar dependencias

pip install -r requirements.txt

### 2. Levantar servicios con Docker

docker-compose up -d

Esto levanta:
- Kafka en `localhost:9092`
- MariaDB en `localhost:3306`

### 3. Crear topics de Kafka

**Windows:**
crear_topics.bat

### 4. Verificar conexiones

python test_conexiones.py

## Uso

### Ejecutar EV_Central

cd EV_Central
python main.py 5000 localhost:9092 localhost:3306

Parámetros:
- `5000` - Puerto socket para CPs
- `localhost:9092` - Servidor Kafka
- `localhost:3306` - Servidor MariaDB

Se abrirá una interfaz gráfica mostrando:
- Estado de todos los Charging Points
- Estadísticas en tiempo real
- Controles para parar/reanudar CPs

## Estructura del Proyecto

sd-prac1/
├── EV_Central/           # Módulo central
│   ├── main.py          # Punto de entrada
│   ├── panel_gui.py     # Interfaz gráfica
│   ├── database.py      # Gestión BD
│   ├── kafka_handler.py # Gestión Kafka
│   └── ...
├── init-db/             # Scripts SQL
├── compose.yml          # Docker Compose
└── requirements.txt     # Dependencias

## Configuración

**Base de datos:**
- Usuario: `evuser`
- Password: `evpass123`
- Database: `evcharging_db`
