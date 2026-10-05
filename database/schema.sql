-- ---------------------------------------------------------------------
-- Fitness & Nutrition Recommendation System - MySQL schema
--
-- Run this once to create the database and tables, e.g.:
--   mysql -u root -p < database/schema.sql
--
-- Flask-SQLAlchemy will also auto-create these tables on first app run
-- (see app/__init__.py -> db.create_all()), but this file is provided
-- so the schema can be reviewed, version-controlled, and applied
-- directly by a DBA without needing to run the Python app first.
-- ---------------------------------------------------------------------

CREATE DATABASE IF NOT EXISTS fitness_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE fitness_db;

-- Dedicated application user with least-privilege access.
-- Change 'change-this-password' before running in any real environment,
-- and make sure it matches DB_PASSWORD in your .env file.
CREATE USER IF NOT EXISTS 'fitness_user'@'localhost' IDENTIFIED BY 'change-this-password';
GRANT SELECT, INSERT, UPDATE, DELETE ON fitness_db.* TO 'fitness_user'@'localhost';
FLUSH PRIVILEGES;

-- ---------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id                    INT AUTO_INCREMENT PRIMARY KEY,
    name                  VARCHAR(120)      NOT NULL,
    email                 VARCHAR(255)      NOT NULL,
    password_hash         VARCHAR(255)      NOT NULL,
    is_admin              TINYINT(1)        NOT NULL DEFAULT 0,
    is_active             TINYINT(1)        NOT NULL DEFAULT 1,
    failed_login_attempts INT               NOT NULL DEFAULT 0,
    locked_until          DATETIME          NULL,
    created_at            DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at         DATETIME          NULL,
    UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- plan_history
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plan_history (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT           NOT NULL,
    goal            VARCHAR(50),
    activity_level  VARCHAR(50),
    targeted_muscle VARCHAR(50),
    difficulty      INT,
    num_weeks       INT,
    diet_type       VARCHAR(50),
    age             INT,
    gender          VARCHAR(20),
    height_cm       FLOAT,
    weight_kg       FLOAT,
    daily_calories  FLOAT,
    protein         FLOAT,
    carbs           FLOAT,
    fats            FLOAT,
    plan_json       LONGTEXT,
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_plan_history_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    KEY idx_plan_history_user_id (user_id),
    KEY idx_plan_history_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Optional: promote an existing user to admin, e.g.:
-- UPDATE users SET is_admin = 1 WHERE email = 'you@example.com';
-- ---------------------------------------------------------------------
