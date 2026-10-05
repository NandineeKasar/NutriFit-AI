-- Run ONCE as MySQL root to add the Progress tracking table:
--   mysql -u root -p < database/progress_logs.sql
-- (The app's least-privilege user 'fitness_user' cannot create tables.)

USE fitness_db;

CREATE TABLE IF NOT EXISTS progress_logs (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT      NOT NULL,
    log_date      DATE     NOT NULL,
    weight_kg     FLOAT    NOT NULL,
    workouts_done INT      NOT NULL DEFAULT 0,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_progress_user_date (user_id, log_date),
    INDEX ix_progress_logs_user_id (user_id),
    INDEX ix_progress_logs_log_date (log_date),
    CONSTRAINT fk_progress_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
