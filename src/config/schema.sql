-- Users table schema
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255),
  username VARCHAR(100),
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  phone VARCHAR(20),
  profile_picture_url TEXT,
  google_oauth_id VARCHAR(255),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_google_oauth_id ON users(google_oauth_id);

-- Create views if needed
CREATE OR REPLACE VIEW user_profiles AS
SELECT 
  id, 
  email, 
  username, 
  first_name, 
  last_name, 
  profile_picture_url,
  created_at
FROM users; 