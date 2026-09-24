-- Create database
CREATE DATABASE IF NOT EXISTS security_awareness;
USE security_awareness;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('user', 'admin') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Questions Table
CREATE TABLE IF NOT EXISTS questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question TEXT NOT NULL,
    option_a VARCHAR(255) NOT NULL,
    option_b VARCHAR(255) NOT NULL,
    option_c VARCHAR(255) NOT NULL,
    option_d VARCHAR(255) NOT NULL,
    correct_answer ENUM('A', 'B', 'C', 'D') NOT NULL,
    category VARCHAR(50) NOT NULL,
    difficulty ENUM('Easy', 'Medium', 'Hard') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Quiz Results Table
CREATE TABLE IF NOT EXISTS quiz_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    score INT NOT NULL,
    total_questions INT NOT NULL,
    percentage DECIMAL(5,2) NOT NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Quiz Answers Table
CREATE TABLE IF NOT EXISTS quiz_answers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    result_id INT NOT NULL,
    question_id INT NOT NULL,
    selected_answer ENUM('A', 'B', 'C', 'D') NULL,
    is_correct BOOLEAN NOT NULL,
    FOREIGN KEY (result_id) REFERENCES quiz_results(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- Insert Default Admin (Password is 'admin123')
-- Hashed using Werkzeug scrypt
INSERT INTO users (username, email, password, role) 
VALUES ('admin', 'admin@system.com', 'scrypt:32768:8:1$73rIu0Z9hLzYQ01s$25be15c26dbf59265691c95101fa959a41de1f0a28f4cc1d84f88417537bead8682a3c7bc37996c56858e37dc91d30f30501f11ab9c02c63eb379893d198305c', 'admin');

-- Insert 15 Sample Cybersecurity Questions
INSERT INTO questions (question, option_a, option_b, option_c, option_d, correct_answer, category, difficulty) VALUES
('What is a phishing attack?', 'A network firewall feature', 'An attempt to trick users into revealing sensitive information', 'A type of computer virus', 'A method to secure passwords', 'B', 'Phishing', 'Easy'),
('Which of the following makes a strong password?', 'Using your pet''s name', 'Using "password123"', 'A mix of uppercase, lowercase, numbers, and symbols', 'Your date of birth', 'C', 'Password Security', 'Easy'),
('What does MFA stand for?', 'Multiple File Access', 'Multi-Factor Authentication', 'Malware Finding Application', 'Main Frame Architecture', 'B', 'Password Security', 'Easy'),
('Why is public Wi-Fi considered risky?', 'It drains battery faster', 'It is usually too slow', 'Data transmitted can be intercepted easily by attackers', 'It requires a paid subscription', 'C', 'Network Security', 'Medium'),
('What is ransomware?', 'Software that optimizes your PC', 'Malware that encrypts your files and demands payment', 'An antivirus program', 'A type of hardware wallet', 'B', 'Malware', 'Medium'),
('What should you look for in a URL to ensure the connection is encrypted?', 'http://', 'www.', '.com', 'https://', 'D', 'Safe Browsing', 'Easy'),
('What is Social Engineering?', 'Building social media platforms', 'Manipulating people into breaking normal security procedures', 'Networking with IT professionals', 'A firewall protocol', 'B', 'Social Engineering', 'Medium'),
('Which of these is a common sign of a phishing email?', 'Personalized greeting with your full name', 'Urgent language demanding immediate action', 'Emails from your boss', 'Proper spelling and grammar', 'B', 'Email Security', 'Medium'),
('What is a Trojan Horse in cybersecurity?', 'A firewall brand', 'A secure encrypted vault', 'Malware disguised as legitimate software', 'A network router', 'C', 'Malware', 'Medium'),
('Why should you not reuse passwords across multiple sites?', 'It uses too much memory', 'If one site is breached, all your accounts are compromised', 'Websites will block you', 'It makes the internet slower', 'B', 'Password Security', 'Medium'),
('What is Data Privacy?', 'Hiding your computer monitor', 'The proper handling, processing, and storage of personal information', 'Deleting all files daily', 'Using incognito mode only', 'B', 'Data Privacy', 'Medium'),
('What does a VPN do?', 'Makes your computer immune to viruses', 'Encrypts your internet traffic and hides your IP address', 'Speeds up your internet connection automatically', 'Cleans your keyboard', 'B', 'Network Security', 'Hard'),
('What is spyware?', 'Software that secretly monitors and collects your information', 'A tool used by administrators to fix networks', 'A secure messaging app', 'A device used for physical security', 'A', 'Malware', 'Hard'),
('If you receive an unexpected email with an attachment from an unknown sender, you should:', 'Open it immediately', 'Forward it to all your friends', 'Delete it or report it as spam without opening', 'Reply and ask who they are', 'C', 'Email Security', 'Easy'),
('What is the main purpose of a firewall?', 'To keep the computer from overheating', 'To monitor and control incoming and outgoing network traffic', 'To store passwords safely', 'To backup data to the cloud', 'B', 'Network Security', 'Medium');