#!/bin/bash
# Script para crear los topics de Kafka necesarios para EVCharging

echo "Creando topics de Kafka..."

docker exec -it broker_evcharging kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic solicitudes_suministro \
  --partitions 1 \
  --replication-factor 1 \
  --if-not-exists

docker exec -it broker_evcharging kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic respuestas_conductor \
  --partitions 1 \
  --replication-factor 1 \
  --if-not-exists

docker exec -it broker_evcharging kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic comandos_cp \
  --partitions 1 \
  --replication-factor 1 \
  --if-not-exists

docker exec -it broker_evcharging kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic telemetria_cp \
  --partitions 1 \
  --replication-factor 1 \
  --if-not-exists

docker exec -it broker_evcharging kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic fin_suministro \
  --partitions 1 \
  --replication-factor 1 \
  --if-not-exists

docker exec -it broker_evcharging kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic averias \
  --partitions 1 \
  --replication-factor 1 \
  --if-not-exists

docker exec -it broker_evcharging kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic recuperacion_cp \
  --partitions 1 \
  --replication-factor 1 \
  --if-not-exists

docker exec -it broker_evcharging kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic tickets \
  --partitions 1 \
  --replication-factor 1 \
  --if-not-exists

docker exec -it broker_evcharging kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic notificaciones \
  --partitions 1 \
  --replication-factor 1 \
  --if-not-exists

echo "✓ Topics creados. Listado de topics:"
docker exec -it broker_evcharging kafka-topics --list --bootstrap-server localhost:9092