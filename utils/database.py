import pymysql
import os
from datetime import datetime
from utils.config import get_db_config

# Database configuration from core-config.yaml
db_config = get_db_config()

DB_CONFIG = {
    "host": db_config.get("host", "localhost"),
    "user": db_config.get("username", "root"),
    "password": db_config.get("password", ""),
    "database": db_config.get("name", "grantms"),
    "charset": db_config.get("charset", "utf8mb4"),
    "cursorclass": pymysql.cursors.DictCursor,
}


def get_db():
    """Get a MySQL database connection."""
    return pymysql.connect(**DB_CONFIG)


def init_db():
    """Initialize database with tables if they don't exist."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            # Users table (name, email, company; password or OAuth)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255),
                    username VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255),
                    company_name VARCHAR(255),
                    company_description TEXT,
                    auth_provider VARCHAR(50),
                    auth_provider_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            # Migrate existing table: add new columns if missing (for existing DBs)
            for col_sql in [
                "ALTER TABLE users ADD COLUMN name VARCHAR(255) AFTER id",
                "ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) AFTER company_description",
                "ALTER TABLE users ADD COLUMN auth_provider_id VARCHAR(255) AFTER auth_provider",
                "ALTER TABLE users MODIFY COLUMN password VARCHAR(255) NULL",
            ]:
                try:
                    cursor.execute(col_sql)
                    connection.commit()
                except (pymysql.OperationalError, pymysql.InternalError) as e:
                    if "Duplicate column" in str(e) or "1060" in str(e):
                        pass
                    else:
                        raise

            # Grants table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grants (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    agency VARCHAR(255) NOT NULL,
                    description TEXT,
                    funding_amount DECIMAL(15, 2),
                    deadline VARCHAR(255),
                    category VARCHAR(255),
                    location VARCHAR(255),
                    eligibility TEXT,
                    url VARCHAR(2048),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # User Grants table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_grants (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    grant_id INT NOT NULL,
                    status VARCHAR(50) DEFAULT 'Applied',
                    applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (grant_id) REFERENCES grants(id),
                    UNIQUE(user_id, grant_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # Favorites table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    grant_id INT NOT NULL,
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (grant_id) REFERENCES grants(id),
                    UNIQUE(user_id, grant_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # Contact / quote submissions (separate from users - no login)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contact_submissions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    contact_type VARCHAR(50) NOT NULL DEFAULT 'contact',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # Password reset tokens (for forgot password)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    token VARCHAR(255) NOT NULL UNIQUE,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            connection.commit()
    finally:
        connection.close()


# User operations
def create_user(name, email, password_hash, company_name, username=None):
    """Create a new user (sign up with email/password). username defaults to email."""
    if username is None:
        username = email
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users (name, username, email, password, company_name)
                VALUES (%s, %s, %s, %s, %s)
            """, (name or "", username, email, password_hash, company_name or ""))
            connection.commit()
            return cursor.lastrowid
    finally:
        connection.close()


def get_user_by_email(email):
    """Get user by email."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            return cursor.fetchone()
    finally:
        connection.close()


def get_user_by_oauth(provider, provider_id):
    """Get user by OAuth provider and provider id."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE auth_provider = %s AND auth_provider_id = %s",
                (provider, provider_id),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def create_oauth_user(email, name, company_name, provider, provider_id):
    """Create or link user from OAuth. username = email for uniqueness."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users (name, username, email, password, company_name, auth_provider, auth_provider_id)
                VALUES (%s, %s, %s, NULL, %s, %s, %s)
            """, (name or "", email, email, company_name or "", provider, provider_id))
            connection.commit()
            return cursor.lastrowid
    finally:
        connection.close()


def get_user_by_id(user_id):
    """Get user by ID."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()
    finally:
        connection.close()


def get_user_by_username(username):
    """Get user by username."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cursor.fetchone()
    finally:
        connection.close()


def link_oauth_to_user(user_id, provider, provider_id):
    """Link OAuth provider to existing user (e.g. after first email signup)."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE users SET auth_provider = %s, auth_provider_id = %s
                WHERE id = %s
            """, (provider, provider_id, user_id))
            connection.commit()
            return cursor.rowcount
    finally:
        connection.close()


def update_user_profile(user_id):
    """Update user profile (reserved for future profile fields)."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            connection.commit()
            return 1
    finally:
        connection.close()


# Contact / quote submissions (separate from users - no login)
def create_contact_submission(name, email, message, contact_type="contact"):
    """Save a contact or quote request. Does not create a user account."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO contact_submissions (name, email, message, contact_type)
                VALUES (%s, %s, %s, %s)
            """, (name, email, message, contact_type))
            connection.commit()
            return cursor.lastrowid
    finally:
        connection.close()


# Password reset
def create_reset_token(user_id, token, expires_at):
    """Store a password reset token."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO password_reset_tokens (user_id, token, expires_at)
                VALUES (%s, %s, %s)
            """, (user_id, token, expires_at))
            connection.commit()
            return cursor.lastrowid
    finally:
        connection.close()


def get_reset_token_user_id(token):
    """Get user_id for a valid token; returns None if invalid or expired."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT user_id FROM password_reset_tokens
                WHERE token = %s AND expires_at > NOW()
            """, (token,))
            row = cursor.fetchone()
            return row["user_id"] if row else None
    finally:
        connection.close()


def delete_reset_token(token):
    """Remove a reset token (after use or expiry)."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM password_reset_tokens WHERE token = %s", (token,))
            connection.commit()
            return cursor.rowcount
    finally:
        connection.close()


def update_user_password(user_id, password_hash):
    """Update a user's password (for reset)."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE users SET password = %s WHERE id = %s", (password_hash, user_id))
            connection.commit()
            return cursor.rowcount
    finally:
        connection.close()


# Grant operations
def get_all_grants():
    """Get all grants."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM grants")
            return cursor.fetchall()
    finally:
        connection.close()


def get_grant_by_id(grant_id):
    """Get grant by ID."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM grants WHERE id = %s", (grant_id,))
            return cursor.fetchone()
    finally:
        connection.close()


# User Grants operations
def apply_for_grant(user_id, grant_id):
    """Apply for a grant."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_grants (user_id, grant_id, status)
                VALUES (%s, %s, 'Applied')
                ON DUPLICATE KEY UPDATE status = 'Applied', applied_date = CURRENT_TIMESTAMP
            """, (user_id, grant_id))
            connection.commit()
            return cursor.lastrowid if cursor.lastrowid else True
    finally:
        connection.close()


def update_grant_status(user_id, grant_id, status):
    """Update grant application status."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE user_grants SET status = %s
                WHERE user_id = %s AND grant_id = %s
            """, (status, user_id, grant_id))
            connection.commit()
            return cursor.rowcount
    finally:
        connection.close()


def get_user_grants(user_id):
    """Get grants applied by a user."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT g.*, ug.status, ug.applied_date, ug.notes
                FROM user_grants ug
                JOIN grants g ON ug.grant_id = g.id
                WHERE ug.user_id = %s
                ORDER BY ug.applied_date DESC
            """, (user_id,))
            return cursor.fetchall()
    finally:
        connection.close()


# Favorites operations
def add_favorite(user_id, grant_id):
    """Add grant to favorites."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO favorites (user_id, grant_id)
                VALUES (%s, %s)
            """, (user_id, grant_id))
            connection.commit()
            return cursor.lastrowid
    except pymysql.IntegrityError:
        # Already exists, return False
        return False
    finally:
        connection.close()


def remove_favorite(user_id, grant_id):
    """Remove grant from favorites."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM favorites
                WHERE user_id = %s AND grant_id = %s
            """, (user_id, grant_id))
            connection.commit()
            return cursor.rowcount
    finally:
        connection.close()


def is_favorite(user_id, grant_id):
    """Check if grant is favorited by user."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id FROM favorites
                WHERE user_id = %s AND grant_id = %s
            """, (user_id, grant_id))
            return cursor.fetchone() is not None
    finally:
        connection.close()


def get_user_favorites(user_id):
    """Get user's favorite grants."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT g.*, f.saved_at
                FROM favorites f
                JOIN grants g ON f.grant_id = g.id
                WHERE f.user_id = %s
                ORDER BY f.saved_at DESC
            """, (user_id,))
            return cursor.fetchall()
    finally:
        connection.close()
