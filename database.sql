-- Table for storing user data
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    discord_id BIGINT UNIQUE,
    username VARCHAR(255)
);

-- Table for storing guild information
CREATE TABLE guild_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT UNIQUE,
    guild_owner VARCHAR(255),
    discord_name VARCHAR(255),
    roles JSON
);

-- Table for storing admins
CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    discord_id BIGINT UNIQUE,
    username VARCHAR(255)
);

-- Table for storing owners
CREATE TABLE owners (
    id INT AUTO_INCREMENT PRIMARY KEY,
    discord_id BIGINT UNIQUE
);

-- Table for storing user actions
CREATE TABLE user_actions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,
    action_type ENUM('ban', 'kick', 'give_role', 'removeadmin', 'addadmin'),
    reason VARCHAR(255),
    role_id BIGINT, -- Updated role_id field to BIGINT
    FOREIGN KEY (user_id) REFERENCES users(discord_id)
);

-- Table for storing authenticated users
CREATE TABLE authenticated_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    discord_id BIGINT,
    FOREIGN KEY (discord_id) REFERENCES users(discord_id)
);
