# Grant Roadmap

An AI-powered platform that connects you with the best non-dilutive funding opportunities — helping you apply quickly and get approved faster.

## Prerequisites

Before running this application, ensure you have the following installed:

- **Python** 3.8 or higher
- **MySQL** 5.7 or higher
- **pip** (Python package manager)

## Database Setup

This application requires a **MySQL database** named:

```
grantms
```

### Creating the Database

1. **Open MySQL Command Line or MySQL Workbench**

2. **Create the database:**
   ```sql
   CREATE DATABASE grantms;
   ```

3. **Verify the database was created:**
   ```sql
   SHOW DATABASES;
   ```

### Database Configuration

Update your database credentials in the configuration file:
- Check `core-config.yaml` for database connection settings
- Ensure the database host, username, and password match your MySQL setup

## Installation

1. **Clone or Navigate to the project directory:**
   ```bash
   cd c:\Users\uday\Praiselin\Workspace\grantms
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - **Windows:**
     ```bash
     venv\Scripts\activate
     ```
   - **macOS/Linux:**
     ```bash
     source venv/bin/activate
     ```

4. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. **Ensure the MySQL database is running**

2. **Start the Flask application:**
   ```bash
   python app.py
   ```

3. **Access the application in your browser:**
   ```
   http://localhost:5000
   ```

## Project Structure

```
grantms/
├── app.py                 # Main Flask application
├── core-config.yaml       # Configuration file
├── requirements.txt       # Python dependencies
├── static/               # Static files (CSS, JavaScript, images)
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   └── image/
├── templates/            # HTML templates
│   ├── layout.html
│   ├── dashboard.html
│   ├── plans.html
│   ├── services.html
│   ├── resources.html
│   ├── signin.html
│   └── signup.html
└── utils/               # Utility modules
    ├── __init__.py
    ├── config.py
    ├── database.py
    └── __pycache__/
```

## Configuration

Edit `core-config.yaml` to configure:
- Database connection settings
- Application settings
- Feature toggles
- API configurations

### Sign-in with Google, Microsoft, or Apple (optional)

To enable "Sign in with Google", "Sign in with Microsoft", or "Sign in with Apple", add OAuth credentials.

1. **In `core-config.yaml`** under `oauth` > `google` / `microsoft` / `apple`, set `client_id` and `client_secret` (from each provider’s developer console).
2. **Or use environment variables** (recommended for production):
   - Google: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
   - Microsoft: `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`
   - Apple: `APPLE_CLIENT_ID`, `APPLE_CLIENT_SECRET` (Apple also needs a JWT client secret in many setups).

3. **Redirect URI** to register with each provider:
   - Google: `http://localhost:5000/auth/google/callback` (use your real domain in production)
   - Microsoft: `http://localhost:5000/auth/microsoft/callback`
   - Apple: `http://localhost:5000/auth/apple/callback`

If a provider is not configured, its button is still shown but users see a “not configured” message when they click it.
