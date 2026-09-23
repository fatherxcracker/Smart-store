-- 1. Create the Database
CREATE DATABASE IF NOT EXISTS `smart_store_db`;
USE `smart_store_db`;

-- 2. Create the Customers Table
CREATE TABLE IF NOT EXISTS `customers` (
    `customer_id` INT AUTO_INCREMENT PRIMARY KEY,
    `full_name` VARCHAR(100) NOT NULL,
    `address` VARCHAR(255) NOT NULL,
    `telephone_number` VARCHAR(20) NOT NULL,
    `email_address` VARCHAR(100) NOT NULL UNIQUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Create the System Logs Table (for monitoring LEDs & Buzzer actions)
CREATE TABLE IF NOT EXISTS `system_logs` (
    `log_id` INT AUTO_INCREMENT PRIMARY KEY,
    `customer_email` VARCHAR(100),
    `status` ENUM('SUCCESS', 'FAILURE') NOT NULL,
    `blue_led` TINYINT(1) DEFAULT 0,  -- 1 = ON, 0 = OFF
    `red_led` TINYINT(1) DEFAULT 0,   -- 1 = ON, 0 = OFF
    `buzzer` TINYINT(1) DEFAULT 0,    -- 1 = ON, 0 = OFF
    `message` VARCHAR(255) NOT NULL,
    `logged_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Seed Data for Customers Table
INSERT INTO `customers` (`full_name`, `address`, `telephone_number`, `email_address`) VALUES
('John Doe', '123 Maple Street, Montreal, QC', '514-555-0199', 'john.doe@email.com'),
('Jane Smith', '456 Oak Avenue, Toronto, ON', '416-555-0234', 'jane.smith@email.com'),
('Alex Rivera', '789 Pine Road, Vancouver, BC', '604-555-0876', 'alex.r@email.com');

-- 5. Seed Data for System Logs (Simulating successful and failed insertion triggers)
INSERT INTO `system_logs` (`customer_email`, `status`, `blue_led`, `red_led`, `buzzer`, `message`) VALUES
('john.doe@email.com', 'SUCCESS', 1, 0, 0, 'Customer added successfully. Notification triggered.'),
('jane.smith@email.com', 'SUCCESS', 1, 0, 0, 'Customer added successfully. Notification triggered.'),
('duplicate.email@email.com', 'FAILURE', 0, 1, 1, 'Error: Duplicate entry or missing required field. Action failed.');
