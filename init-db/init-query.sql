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

-- Datos de prueba
INSERT INTO conductores (id, nombre, apellidos, email) VALUES
('DRV001', 'Juan', 'García Martínez', 'juan.garcia@test.com'),
('DRV002', 'María', 'López Sánchez', 'maria.lopez@test.com'),
('DRV003', 'Carlos', 'Rodríguez Pérez', 'carlos.rodriguez@test.com'),
('DRV004', 'Ana', 'Fernández González', 'ana.fernandez@test.com'),
('DRV005', 'Pedro', 'Martínez Ruiz', 'pedro.martinez@test.com'),
('DRV006', 'Laura', 'González Díaz', 'laura.gonzalez@test.com'),
('DRV007', 'David', 'Sánchez Moreno', 'david.sanchez@test.com'),
('DRV008', 'Carmen', 'Jiménez Castro', 'carmen.jimenez@test.com'),
('DRV009', 'Miguel', 'Romero Navarro', 'miguel.romero@test.com'),
('DRV010', 'Isabel', 'Torres Blanco', 'isabel.torres@test.com'),
('DRV011', 'Francisco', 'Álvarez Herrera', 'francisco.alvarez@test.com'),
('DRV012', 'Lucía', 'Ramírez Molina', 'lucia.ramirez@test.com'),
('DRV013', 'Antonio', 'Vargas Ortiz', 'antonio.vargas@test.com'),
('DRV014', 'Elena', 'Castillo Núñez', 'elena.castillo@test.com'),
('DRV015', 'José', 'Morales Iglesias', 'jose.morales@test.com'),
('DRV016', 'Rosa', 'Delgado Campos', 'rosa.delgado@test.com'),
('DRV017', 'Manuel', 'Vega Fuentes', 'manuel.vega@test.com'),
('DRV018', 'Pilar', 'Mendez Silva', 'pilar.mendez@test.com'),
('DRV019', 'Javier', 'Guerrero Cortés', 'javier.guerrero@test.com'),
('DRV020', 'Beatriz', 'Serrano Ramos', 'beatriz.serrano@test.com');

INSERT INTO charging_points (id, ubicacion, latitud, longitud, precio_kwh, estado) VALUES
('CP001', 'Campus UA - Edificio Politécnica I', 38.384370, -0.512340, 0.350, 'activado'),
('CP002', 'Campus UA - Edificio Politécnica II', 38.385120, -0.511890, 0.350, 'activado'),
('CP003', 'Campus UA - Biblioteca General', 38.383950, -0.513200, 0.380, 'activado'),
('CP004', 'Campus UA - Facultad de Ciencias', 38.382800, -0.510500, 0.350, 'desconectado'),
('CP005', 'Campus UA - Aulario I', 38.384900, -0.512800, 0.360, 'activado'),
('CP006', 'Campus UA - Aulario II', 38.385400, -0.513100, 0.360, 'suministrando'),
('CP007', 'Centro Ciudad - Plaza Mayor', 38.345400, -0.481200, 0.420, 'activado'),
('CP008', 'Centro Ciudad - Parking Central', 38.346800, -0.482500, 0.450, 'activado'),
('CP009', 'Zona Norte - Centro Comercial', 38.358900, -0.490300, 0.400, 'activado'),
('CP010', 'Zona Norte - Polideportivo', 38.360200, -0.491800, 0.380, 'parado'),
('CP011', 'Zona Sur - Hospital General', 38.335600, -0.485900, 0.390, 'activado'),
('CP012', 'Zona Sur - Estación Autobuses', 38.338200, -0.487400, 0.410, 'activado'),
('CP013', 'Zona Este - Polígono Industrial', 38.350800, -0.465200, 0.340, 'activado'),
('CP014', 'Zona Este - Parque Tecnológico', 38.352100, -0.467800, 0.360, 'suministrando'),
('CP015', 'Zona Oeste - Centro Deportivo', 38.348500, -0.505600, 0.370, 'activado'),
('CP016', 'Aeropuerto - Terminal 1', 38.282100, -0.558400, 0.480, 'activado'),
('CP017', 'Aeropuerto - Terminal 2', 38.281500, -0.559800, 0.480, 'activado'),
('CP018', 'Playa - Parking Playa San Juan', 38.386700, -0.433200, 0.400, 'activado'),
('CP019', 'Playa - Paseo Marítimo', 38.388900, -0.430100, 0.410, 'averiado'),
('CP020', 'Montaña - Área Recreativa', 38.455600, -0.543200, 0.390, 'desconectado');