# cr.io - Cryogenic Information Management System

A Streamlit-based Laboratory Information Management System (LIMS) for tracking samples in cryogenic storage.

## Supabase Integration

This application has been updated to use Supabase as a secure cloud database backend. This provides several security benefits:

- Data is stored in a secure PostgreSQL database in the cloud
- Authentication is more secure with bcrypt password hashing
- Rate limiting for login attempts
- Separation of database credentials from application code
- Automatic backups and database management

## Setup Instructions

### 1. Create a Supabase Account and Project

1. Sign up for a free account at [Supabase](https://supabase.com/)
2. Create a new project
3. Note your project URL and API keys (anon key and service role key)

### 2. Set Up Database Tables in Supabase

Create the following tables in your Supabase project using the SQL Editor:

```sql
-- Users table
CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  salt TEXT NOT NULL,
  role TEXT DEFAULT 'user',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_login TIMESTAMP WITH TIME ZONE,
  is_active BOOLEAN DEFAULT TRUE
);

-- Freezers table
CREATE TABLE freezers (
  name TEXT PRIMARY KEY
);

-- Racks table
CREATE TABLE racks (
  id TEXT PRIMARY KEY,
  freezer_name TEXT REFERENCES freezers(name) ON DELETE CASCADE NOT NULL,
  rows INTEGER,
  columns INTEGER
);

-- Boxes table
CREATE TABLE boxes (
  id TEXT,
  rack_id TEXT REFERENCES racks(id) ON DELETE CASCADE,
  freezer_name TEXT REFERENCES freezers(name) ON DELETE CASCADE,
  box_name TEXT,
  assigned_user TEXT,
  rows INTEGER,
  columns INTEGER,
  PRIMARY KEY (id, rack_id, freezer_name)
);

-- Samples table
CREATE TABLE samples (
  id BIGSERIAL PRIMARY KEY,
  sample_name TEXT,
  sample_type TEXT,
  well TEXT,
  owner TEXT,
  date_added TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  notes TEXT,
  species TEXT,
  resistance TEXT,
  regulation TEXT,
  freezer TEXT NOT NULL,
  rack TEXT NOT NULL,
  box TEXT NOT NULL,
  box_id TEXT NOT NULL,
  rack_id TEXT NOT NULL,
  freezer_name TEXT NOT NULL,
  FOREIGN KEY (box_id, rack_id, freezer_name) REFERENCES boxes(id, rack_id, freezer_name) ON DELETE CASCADE
);

-- Sample history table
CREATE TABLE sample_history (
  id BIGSERIAL PRIMARY KEY,
  sample_id BIGINT REFERENCES samples(id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  field TEXT,
  old_value TEXT,
  new_value TEXT,
  user_id BIGINT,
  username TEXT,
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  freezer TEXT,
  rack TEXT,
  box TEXT,
  well TEXT,
  sample_name TEXT
);
```

# Supabase credentials

Create a .toml file for the secrets area of your streamlit app, an example is provided below:

[supabase]
url = "https://yourproject.supabase.co"
key = "your_key"
service_key = "your_service_key"

# Admin settings
[admin]
initial_password = "a_strong_password"

# Environment settings
[environment]
mode = "development"

## Deploying to Streamlit Cloud

1. Push your code to a GitHub repository

2. Log in to [Streamlit Cloud](https://streamlit.io/cloud)

3. Create a new app and connect it to your GitHub repository

4. Set the main file path to `app/app_supabase.py`

5. Add your Supabase credentials as secrets in the Streamlit Cloud dashboard:
   ```toml
   [supabase]
   url = "https://your-project-url.supabase.co"
   key = "your-supabase-anon-key"
   service_key = "your-supabase-service-role-key"

   [admin]
   initial_password = "your-admin-password"
   ```

6. Deploy the app

## Security Best Practices

1. **Use Strong Passwords**: Ensure all user accounts have strong, unique passwords

2. **Regular Backups**: Supabase provides automatic backups, but you can also export your data regularly

3. **Access Control**: Use the role-based access control system to limit user permissions

4. **Audit Logs**: Review the sample history logs regularly to monitor for suspicious activity

5. **Update Dependencies**: Keep all dependencies updated to patch security vulnerabilities

6. **Enable Streamlit Authentication**: When deploying to Streamlit Cloud, enable their built-in authentication for an additional layer of security

## Additional Security Measures

1. **IP Restrictions**: Consider restricting access to your Supabase database by IP address

2. **Database Encryption**: Supabase provides encryption at rest for your data

3. **Regular Security Audits**: Periodically review your application's security settings

4. **Monitoring**: Set up alerts for unusual database activity

## Troubleshooting

- **Connection Issues**: Ensure your Supabase credentials are correct and that your IP is not blocked
- **Authentication Problems**: Check that the users table is properly set up in Supabase
- **Data Access Errors**: Verify that your Supabase policies allow the necessary operations