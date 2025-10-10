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
    latitud DECIMAL(8, 6) NOT NULL,
    longitud DECIMAL(9, 6) NOT NULL,
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

-- Datos de prueba - Conductores (solo IDs)
INSERT INTO conductores (id) VALUES
('DRV001'), ('DRV002'), ('DRV003'), ('DRV004'), ('DRV005'),
('DRV006'), ('DRV007'), ('DRV008'), ('DRV009'), ('DRV010'),
('DRV011'), ('DRV012'), ('DRV013'), ('DRV014'), ('DRV015'),
('DRV016'), ('DRV017'), ('DRV018'), ('DRV019'), ('DRV020');

-- Datos de prueba - Charging Points
INSERT INTO charging_points (id, estado) VALUES
('CP001', 'desconectado'),
('CP002', 'desconectado'),
('CP003', 'desconectado'),
('CP004', 'desconectado'),
('CP005', 'desconectado'),
('CP006', 'desconectado'),
('CP007', 'desconectado'),
('CP008', 'desconectado'),
('CP009', 'desconectado'),
('CP010', 'desconectado'),
('CP011', 'desconectado'),
('CP012', 'desconectado'),
('CP013', 'desconectado'),
('CP014', 'desconectado'),
('CP015', 'desconectado'),
('CP016', 'desconectado'),
('CP017', 'desconectado'),
('CP018', 'desconectado'),
('CP019', 'desconectado'),
('CP020', 'desconectado');