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
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    company_name VARCHAR(255),
                    company_description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

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

            # Check if grants table has data, if not seed it
            cursor.execute("SELECT COUNT(*) as count FROM grants")
            if cursor.fetchone()["count"] == 0:
                sample_grants = [
                    ("Small Business Innovation Grant", "Gov Agency A", "Supports innovative small business projects in technology and R&D.", 50000, "2024-12-31", "Technology", "Canada", "Small businesses with < 250 employees", "https://example.com/grant1"),
                    ("Green Energy Adoption Grant", "Gov Agency B", "Funding for companies adopting green energy solutions.", 100000, "2024-11-30", "Sustainability", "Canada", "All business sizes", "https://example.com/grant2"),
                    ("Workforce Training Grant", "Gov Agency C", "Supports training programs to upskill employees.", 30000, "2024-10-31", "HR/Training", "Canada", "Organizations with 10+ employees", "https://example.com/grant3"),
                    ("Rural Development Grant", "Gov Agency D", "Grants for companies expanding services in rural areas.", 75000, "2024-09-30", "Expansion", "Rural Canada", "Any organization", "https://example.com/grant4"),
                    ("Export Market Development Grant", "Gov Agency E", "Support for companies entering new export markets.", 50000, "2024-12-15", "Export", "Canada", "SMEs with export plans", "https://example.com/grant5"),
                ]
                
                cursor.executemany("""
                    INSERT INTO grants (title, agency, description, funding_amount, deadline, category, location, eligibility, url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, sample_grants)

            connection.commit()
    finally:
        connection.close()


# User operations
def create_user(username, email, password_hash, company_name):
    """Create a new user."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users (username, email, password, company_name)
                VALUES (%s, %s, %s, %s)
            """, (username, email, password_hash, company_name))
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


def update_user_profile(user_id, company_description):
    """Update user profile."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE users SET company_description = %s
                WHERE id = %s
            """, (company_description, user_id))
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
