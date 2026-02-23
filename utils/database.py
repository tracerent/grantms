import json
import pymysql
import re
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


# Sample grants for dashboard / list building (seed when grants table is empty)
SAMPLE_GRANTS = [
    ("Community Development Block Grant", "U.S. HUD", 75000, "Research & Development"),
    ("Small Business Innovation Research", "U.S. SBA", 150000, "Research & Development"),
    ("Rural Energy for America Program", "USDA", 500000, "Sustainability (ESG)"),
    ("Federal Pell Grant Program", "U.S. Department of Education", 6895, "Training/Upskilling"),
    ("Workforce Innovation and Opportunity Act", "U.S. DOL", 250000, "Hiring"),
    ("Export Development Canada SME Financing", "EDC Canada", 100000, "Expand Internationally"),
    ("Canada Job Grant Program", "Government of Canada", 15000, "Hiring"),
    ("Industrial Research Assistance Program", "NRC IRAP", 10000000, "Research & Development"),
    ("Strategic Innovation Fund", "ISED Canada", 10000000, "Expansion & Scaling"),
    ("Regional Development Agency Grants", "Canadian RDAs", 500000, "Expansion & Scaling"),
]


def _seed_sample_grants(cursor):
    """Insert sample grant rows. Sets status and funding_for when those columns exist."""
    base_desc = "Eligibility and application details available from the funding organization."
    base_eligibility = "See official program guidelines for eligibility requirements."
    for title, agency, funding_amount, category in SAMPLE_GRANTS:
        # Use category for funding_for so List Building filter can match
        cursor.execute(
            """
            INSERT INTO grants (title, agency, description, funding_amount, deadline, category, funding_for, location, eligibility, url, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                title,
                agency,
                base_desc,
                funding_amount,
                "2026-12-31",
                category,
                category,
                "Canada",
                base_eligibility,
                "https://example.com/grant-info",
                "Open",
            ),
        )


def init_db():
    """Initialize database with tables if they don't exist. CREATE only (no ALTER)."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            # Users table
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
                    list_building_filters TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN list_building_filters TEXT AFTER auth_provider_id")
                connection.commit()
            except (pymysql.OperationalError, pymysql.InternalError) as e:
                if "Duplicate column" not in str(e) and "1060" not in str(e):
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
                    funding_for VARCHAR(255),
                    location VARCHAR(255),
                    eligibility TEXT,
                    url VARCHAR(2048),
                    status VARCHAR(50) DEFAULT 'Open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # User Grants table: one row per (user_id, grant_id); year and quarter (numerical) from star flow
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_grants (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    grant_id INT NOT NULL,
                    year INT NOT NULL,
                    quarter INT NOT NULL,
                    status VARCHAR(50) DEFAULT 'Added',
                    applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (grant_id) REFERENCES grants(id),
                    UNIQUE(user_id, grant_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # Seed sample grants if table is empty
            cursor.execute("SELECT COUNT(*) AS n FROM grants")
            if cursor.fetchone()["n"] == 0:
                _seed_sample_grants(cursor)
                connection.commit()

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


def get_user_filter_settings(user_id):
    """Get saved List Building filter settings as a dict. Returns {} if none or invalid JSON."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT list_building_filters FROM users WHERE id = %s",
                (user_id,),
            )
            row = cursor.fetchone()
            if not row or not row.get("list_building_filters"):
                return {}
            try:
                return json.loads(row["list_building_filters"]) or {}
            except (TypeError, ValueError):
                return {}
    finally:
        connection.close()


def save_user_filter_settings(user_id, filters_dict):
    """Save List Building filter settings. filters_dict should be JSON-serializable (e.g. {status: '', funding_for: ''})."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET list_building_filters = %s WHERE id = %s",
                (json.dumps(filters_dict or {}), user_id),
            )
            connection.commit()
            return cursor.rowcount
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
def _current_year_quarter():
    """Return (year, quarter) for current date. Quarter is 1-4."""
    now = datetime.now()
    return (now.year, (now.month - 1) // 3 + 1)


def _parse_quarter_string(quarter_str):
    """Parse '2026 Q2' to (year, quarter). Quarter 1-4. Returns (None, None) if invalid."""
    if not quarter_str or not isinstance(quarter_str, str):
        return (None, None)
    s = quarter_str.strip()
    m = re.match(r"(\d{4})\s*[Qq]\s*([1-4])$", s)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return (None, None)


def apply_for_grant(user_id, grant_id):
    """Apply for a grant (insert with current year/quarter)."""
    year, quarter = _current_year_quarter()
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_grants (user_id, grant_id, year, quarter, status)
                VALUES (%s, %s, %s, %s, 'Applied')
                ON DUPLICATE KEY UPDATE status = 'Applied', year = %s, quarter = %s, applied_date = CURRENT_TIMESTAMP
            """, (user_id, grant_id, year, quarter, year, quarter))
            connection.commit()
            return cursor.lastrowid if cursor.lastrowid else True
    finally:
        connection.close()


def add_grant_to_portfolio(user_id, grant_id, quarter_str):
    """Add grant to portfolio. quarter_str e.g. '2026 Q2'; stored as year (int) and quarter (int 1-4)."""
    year, quarter = _parse_quarter_string(quarter_str)
    if year is None or quarter is None:
        raise ValueError("Invalid quarter; expected e.g. '2026 Q2'")
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_grants (user_id, grant_id, year, quarter, status)
                VALUES (%s, %s, %s, %s, 'Added')
                ON DUPLICATE KEY UPDATE year = %s, quarter = %s, status = 'Added', applied_date = CURRENT_TIMESTAMP
            """, (user_id, grant_id, year, quarter, year, quarter))
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


def remove_grant_from_portfolio(user_id, grant_id):
    """Remove a grant from the user's portfolio."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM user_grants
                WHERE user_id = %s AND grant_id = %s
            """, (user_id, grant_id))
            connection.commit()
            return cursor.rowcount
    finally:
        connection.close()


def get_user_grants(user_id):
    """Get grants applied by a user (includes portfolio with year and quarter)."""
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT g.*, ug.status, ug.applied_date, ug.notes, ug.year, ug.quarter
                FROM user_grants ug
                JOIN grants g ON ug.grant_id = g.id
                WHERE ug.user_id = %s
                ORDER BY ug.applied_date DESC
            """, (user_id,))
            return cursor.fetchall()
    finally:
        connection.close()


