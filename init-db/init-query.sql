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

-- Datos de prueba - Charging Points (con coordenadas GPS)
INSERT INTO charging_points (id, latitud, longitud, precio_kwh, estado) VALUES
('CP001', 38.384370, -0.512340, 0.350, 'desconectado'),
('CP002', 38.385120, -0.511890, 0.350, 'desconectado'),
('CP003', 38.383950, -0.513200, 0.380, 'desconectado'),
('CP004', 38.382800, -0.510500, 0.350, 'desconectado'),
('CP005', 38.384900, -0.512800, 0.360, 'desconectado'),
('CP006', 38.385400, -0.513100, 0.360, 'desconectado'),
('CP007', 38.345400, -0.481200, 0.420, 'desconectado'),
('CP008', 38.346800, -0.482500, 0.450, 'desconectado'),
('CP009', 38.358900, -0.490300, 0.400, 'desconectado'),
('CP010', 38.360200, -0.491800, 0.380, 'desconectado'),
('CP011', 38.335600, -0.485900, 0.390, 'desconectado'),
('CP012', 38.338200, -0.487400, 0.410, 'desconectado'),
('CP013', 38.350800, -0.465200, 0.340, 'desconectado'),
('CP014', 38.352100, -0.467800, 0.360, 'desconectado'),
('CP015', 38.348500, -0.505600, 0.370, 'desconectado'),
('CP016', 38.282100, -0.558400, 0.480, 'desconectado'),
('CP017', 38.281500, -0.559800, 0.480, 'desconectado'),
('CP018', 38.386700, -0.433200, 0.400, 'desconectado'),
('CP019', 38.388900, -0.430100, 0.410, 'desconectado'),
('CP020', 38.455600, -0.543200, 0.390, 'desconectado');