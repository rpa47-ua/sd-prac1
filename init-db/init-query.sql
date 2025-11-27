CREATE DATABASE IF NOT EXISTS evcharging_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE evcharging_db;

-- Eliminar tablas si existen (para recrearlas)
DROP TABLE IF EXISTS suministros;
DROP TABLE IF EXISTS auditoria;
DROP TABLE IF EXISTS charging_points;
DROP TABLE IF EXISTS conductores;

-- Tabla de Conductores (mínima - solo ID para tickets y recuperación)
CREATE TABLE conductores (
    id VARCHAR(50) PRIMARY KEY,
    conectado BOOLEAN DEFAULT FALSE,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Tabla de Charging Points (con coordenadas GPS y seguridad)
CREATE TABLE charging_points (
    id VARCHAR(50) PRIMARY KEY,
    estado ENUM('desconectado', 'activado', 'parado', 'suministrando', 'averiado') DEFAULT 'desconectado',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Campos de cifrado y autenticación
    clave_cifrado VARCHAR(255) DEFAULT NULL COMMENT 'Clave simétrica única para cifrado de mensajes',
    fecha_generacion_clave TIMESTAMP NULL COMMENT 'Fecha de generación de la clave de cifrado',
    -- Campos para localización meteorológica
    latitud DECIMAL(10, 8) DEFAULT NULL COMMENT 'Latitud GPS del CP',
    longitud DECIMAL(11, 8) DEFAULT NULL COMMENT 'Longitud GPS del CP',
    estado_meteorologico VARCHAR(100) DEFAULT NULL COMMENT 'Estado del clima actual',
    alerta_meteorologica BOOLEAN DEFAULT FALSE COMMENT 'Indica si hay alerta meteorológica activa'
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
    ticket_enviado BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (conductor_id) REFERENCES conductores(id),
    FOREIGN KEY (cp_id) REFERENCES charging_points(id)
) ENGINE=InnoDB;

-- Tabla de Auditoría de Eventos
CREATE TABLE auditoria (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_origen VARCHAR(45) COMMENT 'Dirección IP del origen del evento',
    modulo VARCHAR(50) COMMENT 'Módulo que generó el evento (Central, CP, Driver, etc)',
    accion VARCHAR(100) COMMENT 'Acción realizada',
    parametros TEXT COMMENT 'Parámetros de la acción en formato JSON',
    resultado VARCHAR(20) COMMENT 'Resultado de la acción (éxito, error)',
    detalle TEXT COMMENT 'Detalle adicional del evento',
    INDEX idx_timestamp (timestamp),
    INDEX idx_modulo (modulo),
    INDEX idx_accion (accion)
) ENGINE=InnoDB;
