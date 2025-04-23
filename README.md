# cr.io - Cryogenic Information Management System

A Streamlit-based Laboratory Information Management System (LIMS) for tracking samples in cryogenic storage. This application helps laboratories manage their freezer inventory, track samples, and maintain a complete history of sample movements and modifications.

## Features

- **Hierarchical Storage Management**: Organize samples in freezers, racks, and boxes
- **Sample Tracking**: Track sample details, locations, and history
- **User Management**: Role-based access control (admin, user, readonly)
- **Search Capabilities**: Find samples quickly with basic and advanced search
- **Data Visualization**: Analyze storage utilization and sample distribution
- **Secure Cloud Database**: Store data securely in Supabase PostgreSQL database

## Prerequisites

Before you begin, you'll need:

- **GitHub Account**: For forking the repository and deploying to Streamlit Cloud
- **Supabase Account**: For the cloud database (free tier available)
- **Streamlit Cloud Account**: For hosting the application (free tier available)
- **Python 3.8+**: For local development (optional)

## Step-by-Step Setup Guide

### 1. Fork the Repository

1. Visit the [cr.io GitHub repository](https://github.com/yourusername/cr.io)
2. Click the "Fork" button in the top-right corner
3. Clone your forked repository to your local machine (optional for local development):
   ```bash
   git clone https://github.com/yourusername/cr.io.git
   cd cr.io
   ```

### 2. Set Up Supabase

1. **Create a Supabase Account**:
   - Go to [Supabase](https://supabase.com/) and sign up for a free account
   - Verify your email address

2. **Create a New Project**:
   - Click "New Project" in the Supabase dashboard
   - Enter a name for your project (e.g., "cr-io-lims")
   - Set a secure database password (save this for your records)
   - Choose the region closest to your users
   - Click "Create new project"

3. **Get Your API Keys**:
   - Once your project is created, go to the project dashboard
   - In the left sidebar, click "Project Settings" → "API"
   - Note down your:
     - Project URL (e.g., https://abcdefghijklm.supabase.co)
     - `anon` public key (starts with "eyJ...")
     - `service_role` secret key (for admin operations)

4. **Create Database Tables**:
   - In the left sidebar, click "SQL Editor"
   - Click "New Query"
   - Copy and paste the following SQL code:

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

5. **Run the SQL Query**:
   - Click the "Run" button to create all the tables
   - Verify that all tables were created successfully in the "Table Editor" section

### 3. Local Development Setup (Optional)

If you want to run the application locally before deploying:

1. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Create Environment Variables**:
   - Create a `.env` file in the project root with your Supabase credentials:
   ```
   SUPABASE_URL=https://your-project-url.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   SUPABASE_SERVICE_KEY=your-supabase-service-role-key
   ADMIN_INITIAL_PASSWORD=choose-a-strong-password
   ```

3. **Run the Application Locally**:
   ```bash
   streamlit run app.py
   ```

4. **Access the Application**:
   - Open your browser and go to `http://localhost:8501`
   - The first time you run the app, it will create an admin user with:
     - Username: `admin`
     - Password: The value you set for `ADMIN_INITIAL_PASSWORD`

### 4. Deploy to Streamlit Cloud

1. **Create a Streamlit Account**:
   - Go to [Streamlit Cloud](https://streamlit.io/cloud) and sign up
   - Connect your GitHub account when prompted

2. **Create a New App**:
   - Click "New app" in the Streamlit dashboard
   - Select your forked repository
   - Set the main file path to `app.py`
   - Click "Deploy"

3. **Add Secrets to Streamlit Cloud**:
   - In your deployed app settings, click on "Secrets"
   - Add the following secrets in TOML format:
   ```toml
   [supabase]
   url = "https://your-project-url.supabase.co"
   key = "your-supabase-anon-key"
   service_key = "your-supabase-service-role-key"

   [admin]
   initial_password = "your-admin-password"

   [environment]
   mode = "production"
   ```

4. **Reboot the App**:
   - After adding secrets, click "Reboot app" to apply the changes

5. **Access Your Deployed App**:
   - Click on the URL provided by Streamlit Cloud
   - Log in with the admin credentials (username: `admin`, password: your chosen admin password)

### 5. Initial Configuration

After deploying, you should:

1. **Change the Admin Password**:
   - Log in with the default admin credentials
   - Go to "User Management" → "My Profile"
   - Use the "Change Password" form to set a new secure password

2. **Create Additional Users**:
   - Go to "User Management" → "Add User"
   - Create accounts for your team members with appropriate roles

3. **Add Your First Freezer**:
   - Go to "Sample Management"
   - Use the "Add Freezer" form to create your first freezer
   - Add racks and boxes to organize your storage

## Security Best Practices

1. **Use Strong Passwords**: Ensure all user accounts have strong, unique passwords

2. **Regular Backups**: Supabase provides automatic backups, but you can also export your data regularly

3. **Access Control**: Use the role-based access control system to limit user permissions:
   - **Admin**: Full access to all features, including user management
   - **User**: Can add, edit, and view samples, but cannot manage users
   - **ReadOnly**: Can only view samples, cannot make changes

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
- **Application Errors**: Check the Streamlit Cloud logs for error messages

## Support and Contributions

If you encounter any issues or have suggestions for improvements, please open an issue on the GitHub repository. Contributions are welcome through pull requests!

---

*This project uses Streamlit for the frontend and Supabase for the backend, providing a secure and scalable solution for laboratory sample management.*