-- Employer Satisfaction Evaluation System
-- MySQL 8+ schema only. No sample or test records are inserted.

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS employer_satisfaction
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE employer_satisfaction;

CREATE TABLE IF NOT EXISTS admin (
  id INT NOT NULL AUTO_INCREMENT,
  username VARCHAR(80) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_admin_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS faculty (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(180) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_faculty_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS department (
  id INT NOT NULL AUTO_INCREMENT,
  faculty_id INT NOT NULL,
  name VARCHAR(180) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_department_faculty_name (faculty_id, name),
  KEY ix_department_faculty_id (faculty_id),
  CONSTRAINT fk_department_faculty
    FOREIGN KEY (faculty_id) REFERENCES faculty (id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employer (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(220) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_employer_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS graduate (
  id INT NOT NULL AUTO_INCREMENT,
  code VARCHAR(40) NOT NULL,
  full_name VARCHAR(180) NOT NULL,
  department_id INT NOT NULL,
  job_title VARCHAR(180) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_graduate_code (code),
  KEY ix_graduate_department_id (department_id),
  CONSTRAINT fk_graduate_department
    FOREIGN KEY (department_id) REFERENCES department (id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS graduate_assignment (
  id INT NOT NULL AUTO_INCREMENT,
  employer_id INT NOT NULL,
  graduate_id INT NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_employer_graduate (employer_id, graduate_id),
  KEY ix_graduate_assignment_employer_id (employer_id),
  KEY ix_graduate_assignment_graduate_id (graduate_id),
  CONSTRAINT fk_graduate_assignment_employer
    FOREIGN KEY (employer_id) REFERENCES employer (id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_graduate_assignment_graduate
    FOREIGN KEY (graduate_id) REFERENCES graduate (id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS evaluation_round (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  academic_year VARCHAR(10) NOT NULL,
  is_open TINYINT(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS question_set (
  id INT NOT NULL AUTO_INCREMENT,
  department_id INT NOT NULL,
  name VARCHAR(180) NOT NULL,
  version INT NOT NULL DEFAULT 1,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (id),
  UNIQUE KEY uq_question_set_dept_version (department_id, version),
  KEY ix_question_set_department_id (department_id),
  CONSTRAINT fk_question_set_department
    FOREIGN KEY (department_id) REFERENCES department (id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS question (
  id INT NOT NULL AUTO_INCREMENT,
  question_set_id INT NOT NULL,
  section INT NOT NULL,
  group_name VARCHAR(100) NULL,
  question_code VARCHAR(40) NOT NULL,
  text TEXT NOT NULL,
  sort_order INT NOT NULL DEFAULT 1,
  is_required TINYINT(1) NOT NULL DEFAULT 1,
  allow_na TINYINT(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_question_set_code (question_set_id, question_code),
  KEY ix_question_question_set_id (question_set_id),
  CONSTRAINT fk_question_question_set
    FOREIGN KEY (question_set_id) REFERENCES question_set (id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS evaluation_link (
  id INT NOT NULL AUTO_INCREMENT,
  token VARCHAR(80) NOT NULL,
  department_id INT NOT NULL,
  employer_id INT NOT NULL,
  round_id INT NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (id),
  UNIQUE KEY uq_evaluation_link_token (token),
  UNIQUE KEY uq_link_dept_employer_round (department_id, employer_id, round_id),
  KEY ix_evaluation_link_department_id (department_id),
  KEY ix_evaluation_link_employer_id (employer_id),
  KEY ix_evaluation_link_round_id (round_id),
  CONSTRAINT fk_evaluation_link_department
    FOREIGN KEY (department_id) REFERENCES department (id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_evaluation_link_employer
    FOREIGN KEY (employer_id) REFERENCES employer (id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_evaluation_link_round
    FOREIGN KEY (round_id) REFERENCES evaluation_round (id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS evaluation (
  id INT NOT NULL AUTO_INCREMENT,
  link_id INT NOT NULL,
  round_id INT NOT NULL,
  employer_id INT NOT NULL,
  graduate_id INT NOT NULL,
  question_set_id INT NOT NULL,
  respondent_gender VARCHAR(30) NULL,
  respondent_age VARCHAR(40) NULL,
  respondent_position VARCHAR(180) NULL,
  employer_type VARCHAR(80) NULL,
  work_duration VARCHAR(80) NULL,
  job_alignment VARCHAR(40) NULL,
  submitted_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_evaluation_round_graduate (round_id, graduate_id),
  KEY ix_evaluation_link_id (link_id),
  KEY ix_evaluation_round_id (round_id),
  KEY ix_evaluation_employer_id (employer_id),
  KEY ix_evaluation_graduate_id (graduate_id),
  KEY ix_evaluation_question_set_id (question_set_id),
  CONSTRAINT fk_evaluation_link
    FOREIGN KEY (link_id) REFERENCES evaluation_link (id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_evaluation_round
    FOREIGN KEY (round_id) REFERENCES evaluation_round (id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_evaluation_employer
    FOREIGN KEY (employer_id) REFERENCES employer (id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_evaluation_graduate
    FOREIGN KEY (graduate_id) REFERENCES graduate (id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_evaluation_question_set
    FOREIGN KEY (question_set_id) REFERENCES question_set (id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS evaluation_answer (
  id INT NOT NULL AUTO_INCREMENT,
  evaluation_id INT NOT NULL,
  section INT NOT NULL,
  group_name VARCHAR(100) NULL,
  question_code VARCHAR(40) NOT NULL,
  answer_text TEXT NULL,
  score TINYINT UNSIGNED NULL,
  PRIMARY KEY (id),
  KEY ix_evaluation_answer_evaluation_id (evaluation_id),
  CONSTRAINT fk_evaluation_answer_evaluation
    FOREIGN KEY (evaluation_id) REFERENCES evaluation (id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT chk_evaluation_answer_score
    CHECK (score IS NULL OR score BETWEEN 1 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS import_log (
  id INT NOT NULL AUTO_INCREMENT,
  admin_id INT NULL,
  source_file VARCHAR(255) NOT NULL,
  data_type VARCHAR(80) NOT NULL,
  status VARCHAR(40) NOT NULL,
  rows_seen INT NOT NULL DEFAULT 0,
  rows_imported INT NOT NULL DEFAULT 0,
  rows_rejected INT NOT NULL DEFAULT 0,
  details TEXT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY ix_import_log_admin_id (admin_id),
  CONSTRAINT fk_import_log_admin
    FOREIGN KEY (admin_id) REFERENCES admin (id)
    ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_log (
  id INT NOT NULL AUTO_INCREMENT,
  admin_id INT NULL,
  action VARCHAR(100) NOT NULL,
  entity_type VARCHAR(100) NOT NULL,
  entity_id VARCHAR(80) NULL,
  details TEXT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY ix_audit_log_admin_id (admin_id),
  KEY ix_audit_log_created_at (created_at),
  CONSTRAINT fk_audit_log_admin
    FOREIGN KEY (admin_id) REFERENCES admin (id)
    ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
