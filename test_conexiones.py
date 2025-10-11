"""
Script de prueba para verificar conectividad con Kafka y MariaDB
"""
import sys


def test_mariadb():
    """Prueba conexión a MariaDB"""
    print("[*] Probando conexión a MariaDB...")
    try:
        import pymysql
        conn = pymysql.connect(
            host='localhost',
            port=3306,
            user='evuser',
            password='evpass123',
            database='evcharging_db'
        )
        print("[OK] Conexión a MariaDB exitosa")

        # Probar query simple
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM charging_points")
            result = cursor.fetchone()
            print(f"[OK] CPs en BD: {result[0]}")

        conn.close()
        return True

    except Exception as e:
        print(f"[ERROR] Error conectando a MariaDB: {e}")
        return False


def test_kafka():
    """Prueba conexión a Kafka"""
    print("\n[*] Probando conexión a Kafka...")
    try:
        from confluent_kafka.admin import AdminClient

        admin = AdminClient({'bootstrap.servers': 'localhost:9092'})
        metadata = admin.list_topics(timeout=5)

        print("[OK] Conexión a Kafka exitosa")
        print(f"[OK] Topics existentes: {len(metadata.topics)}")

        return True

    except Exception as e:
        print(f"[ERROR] Error conectando a Kafka: {e}")
        return False


def main():
    print("=" * 60)
    print("TEST DE CONECTIVIDAD - EVCharging System")
    print("=" * 60 + "\n")

    mariadb_ok = test_mariadb()
    kafka_ok = test_kafka()

    print("\n" + "=" * 60)
    if mariadb_ok and kafka_ok:
        print("[OK] TODOS LOS TESTS PASARON - Sistema listo para usar")
    else:
        print("[ERROR] ALGUNOS TESTS FALLARON - Revisar configuración")
        print("\nAsegurate de que Docker Compose esta corriendo:")
        print("  docker-compose -f compose.yml up -d")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
