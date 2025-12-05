📘 README.md — Sistema EV Charging (Versión Definitiva)

📌 Este README está diseñado para usarse tal cual dentro de tu repositorio SD-PRAC1.

⚡ EV Charging System — Guía de despliegue con Docker Compose

Este proyecto implementa un sistema completo de gestión de puntos de carga para vehículos eléctricos, incluyendo:

🗄️ MariaDB

⚡ Apache Kafka (KRaft)

🔌 EV_Central (central del sistema)

🌐 API_Central (API REST para frontend y servicios externos)

🖥️ Frontend Web

🚗 EV_DRIVERS (clientes que solicitan carga)

🟦 EV_CP_E (módulos Energía)

🟩 EV_CP_M (módulos Monitoreo)

📂 1. Estructura del Proyecto
SD-PRAC1/
 ├─ API_Central/
 ├─ EV_Central/
 ├─ EV_CP_E/
 ├─ EV_CP_M/
 ├─ EV_DRIVER/
 ├─ FRONT/
 ├─ init-db/
 ├─ compose.yml
 ├─ crear_topics.bat
 ├─ create_cps.bat
 ├─ create_drivers.bat
 ├─ DESPLIEGUE.md
 ├─ README.md
 ├─ RELEASE2_README.md
 └─ requirements.txt

🧰 2. Requisitos Previos

Docker Desktop

Python 3.8+

Pip instalado

Navegador web

🧱 3. Levantar la Infraestructura con Docker

Desde la carpeta raíz:

cd SD-PRAC1
docker compose -f compose.yml up -d


Esto levantará:

Servicio	Puerto	Descripción
MariaDB	3306	Base de datos
Kafka Broker	9092	Kafka KRaft

Verificar:

docker ps

🗄️ 4. Inicialización Automática de la Base de Datos

El directorio init-db/ contiene:

init-query.sql


El contenedor ejecutará este archivo automáticamente al arrancar.

Verificar las tablas:

docker exec -it evcharging_bbdd mysql -uevuser -pevpass123 evcharging_db -e "SHOW TABLES;"

🔌 5. Iniciar EV_Central
cd EV_Central
python main.py 5000 localhost:9092 localhost:3306


Debes ver:

EV_CENTRAL -> SISTEMA INICIADO CORRECTAMENTE

🌐 6. Iniciar API_Central
cd API_Central
python api_server.py 8000 localhost:3306


Comprobar funcionamiento:

curl http://localhost:8000/health

🖥️ 7. Abrir el Frontend

Opción 1 (directo):

start FRONT\index.html


Opción 2 (servidor opcional):

cd FRONT
python -m http.server 8080


Navegar a:
👉 http://localhost:8080

🔌 8. Crear Puntos de Carga (CPs)

Usar el script:

create_cps.bat 3 localhost


Se abrirán:

3 × ventanas EV_CP_E

3 × ventanas EV_CP_M

En EV_Central verás:

[REGISTRO] Nuevo CP: CP001
[CRYPTO] Clave generada para CP001

🚗 9. Crear Conductores
create_drivers.bat 2 localhost


Se abrirán DRV001 y DRV002.

🔋 10. Realizar un Suministro

En una ventana Driver:

listar
solicitar CP001
ver


Finalizar con:

Ctrl + C


El ticket aparecerá automáticamente.

🌦️ 11. Enviar Alerta Meteorológica
curl -X POST http://localhost:8000/api/weather/alert ^
  -H "Content-Type: application/json" ^
  -d "{\"cp_id\": \"CP001\", \"estado\": \"Tormenta\", \"alerta\": true}"