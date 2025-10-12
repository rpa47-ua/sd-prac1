CREATE DATABASE IF NOT EXISTS evcharging_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE evcharging_db;

-- Eliminar tablas si existen (para recrearlas)
DROP TABLE IF EXISTS suministros;
DROP TABLE IF EXISTS charging_points;
DROP TABLE IF EXISTS conductores;

-- Tabla de Conductores (mínima - solo ID para tickets y recuperación)
CREATE TABLE conductores (
    id VARCHAR(50) PRIMARY KEY,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Tabla de Charging Points (con coordenadas GPS)
CREATE TABLE charging_points (
    id VARCHAR(50) PRIMARY KEY,
    estado ENUM('desconectado', 'activado', 'parado', 'suministrando', 'averiado') DEFAULT 'desconectado',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Tabla de Suministros
CREATE TABLE suministros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conductor_id VARCHAR(50),
    cp_id VARCHAR(50),
    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_fin TIMESTAMP NULL,
    consumo_kwh DECIMAL(8, 3) DEFAULT 0.000,
    importe_total DECIMAL(10, 2) DEFAULT 0.00,
    estado VARCHAR(20) DEFAULT 'solicitado',
    FOREIGN KEY (conductor_id) REFERENCES conductores(id),
    FOREIGN KEY (cp_id) REFERENCES charging_points(id)
) ENGINE=InnoDB;
