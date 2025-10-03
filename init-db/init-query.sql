CREATE DATABASE IF NOT EXISTS evcharging_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE evcharging_db;

-- Tabla de Conductores
CREATE TABLE conductores (
    id VARCHAR(50) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellidos VARCHAR(150) NOT NULL,
    email VARCHAR(100),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Tabla de Charging Points
CREATE TABLE charging_points (
    id VARCHAR(50) PRIMARY KEY,
    ubicacion VARCHAR(250) NOT NULL,
    precio_kwh DECIMAL(6, 3) DEFAULT 0.350,
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

-- Datos de prueba
INSERT INTO conductores (id, nombre, apellidos, email) VALUES
('DRV001', 'Juan', 'García', 'juan@test.com'),
('DRV002', 'María', 'López', 'maria@test.com');

INSERT INTO charging_points (id, ubicacion, estado) VALUES
('CP001', 'Campus UA - Norte', 'activado'),
('CP002', 'Campus UA - Sur', 'desconectado');