-- Create a new database user for the Worldly API project
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/[your-project]/sql/new

-- Step 1: Create the new user with a password
-- Replace 'worldly_api_user' with your preferred username
-- Replace 'your_secure_password_here' with a strong password
CREATE USER worldly_api_user WITH PASSWORD 'your_secure_password_here';

-- Step 2: Grant necessary permissions
-- Grant connection privilege
GRANT CONNECT ON DATABASE postgres TO worldly_api_user;

-- Grant usage on the schema (if using a specific schema like 'worldly')
GRANT USAGE ON SCHEMA worldly TO worldly_api_user;
GRANT USAGE ON SCHEMA public TO worldly_api_user;

-- Grant privileges on existing tables in the worldly schema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA worldly TO worldly_api_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO worldly_api_user;

-- Grant privileges on sequences (for auto-incrementing IDs)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA worldly TO worldly_api_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO worldly_api_user;

-- Step 3: Set default privileges for future tables
-- This ensures new tables created will automatically have the right permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA worldly GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO worldly_api_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA worldly GRANT USAGE, SELECT ON SEQUENCES TO worldly_api_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO worldly_api_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO worldly_api_user;

-- Optional: If you want read-only access instead, use:
-- GRANT SELECT ON ALL TABLES IN SCHEMA worldly TO worldly_api_user;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA worldly GRANT SELECT ON TABLES TO worldly_api_user;

-- Verify the user was created
SELECT usename, usecreatedb, usesuper FROM pg_user WHERE usename = 'worldly_api_user';

