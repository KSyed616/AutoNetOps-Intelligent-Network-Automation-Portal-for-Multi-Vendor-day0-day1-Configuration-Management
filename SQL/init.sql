CREATE DATABASE IF NOT EXISTS AutoNetOps;

USE AutoNetOps;

CREATE TABLE IF NOT EXISTS device (
    device_id INT AUTO_INCREMENT PRIMARY KEY,
    hostname VARCHAR(255),
    ip_address VARCHAR(255),
    platform VARCHAR(255),
    netconf_port INT,
    username VARCHAR(255),
    password VARCHAR(255),
    device_type VARCHAR(255),
    node_id VARCHAR(255)
);


CREATE TABLE IF NOT EXISTS cmlData (
    cml_url VARCHAR(255) PRIMARY KEY,
    username VARCHAR(255),
    password VARCHAR(255),
    token VARCHAR(255),
    lab_id VARCHAR(255)
);


CREATE TABLE IF NOT EXISTS netconf_filters (
    model_name VARCHAR(255) NOT NULL PRIMARY KEY,
    filter_payload VARCHAR(255) NOT NULL,
    UNIQUE(model_name)
);