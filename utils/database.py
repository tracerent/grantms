import json
import pymysql
import re
from datetime import datetime
from utils.config import get_db_config
from utils.utils import Utils

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
# TODO: Remove these when Airtable integration is implemented
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


# Default subscription_id values. First 3 (0,1,2) are system plans and must never be changed.
SUBSCRIPTION_ID_BASIC = 0
SUBSCRIPTION_ID_SUCCESS = 1
SUBSCRIPTION_ID_PREMIUM = 2

class Database:
    """Static methods for all database operations. Use Database.method_name() from app."""
    SUBSCRIPTION_ID_BASIC = 0
    SUBSCRIPTION_ID_SUCCESS = 1
    SUBSCRIPTION_ID_PREMIUM = 2

    @staticmethod
    def init_db():
        """Initialize database: create the database if it doesn't exist, then create all tables if they don't exist. No ALTER or migrations."""
        db_name = DB_CONFIG.get("database", "grantms")
        # Escape backticks in identifier (MySQL); PyMySQL %s is for values, not identifiers
        db_name_escaped = db_name.replace("\\", "\\\\").replace("`", "``")
        conn_without_db = {k: v for k, v in DB_CONFIG.items() if k != "database"}
        try:
            conn = pymysql.connect(**conn_without_db)
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "CREATE DATABASE IF NOT EXISTS `"
                        + db_name_escaped
                        + "` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
                    )
                    conn.commit()
            finally:
                conn.close()
        except Exception:
            pass
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                # Company table first (referenced by users.company_id)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS company (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        legal_entity_name VARCHAR(255),
                        operating_name VARCHAR(255),
                        company_name VARCHAR(255),
                        provincial_corporate_access_number VARCHAR(255),
                        workers_compensation_number VARCHAR(255),
                        business_number VARCHAR(255),
                        business_phone_number VARCHAR(255),
                        address VARCHAR(512),
                        date_of_incorporation DATE,
                        postal_code VARCHAR(32),
                        years_in_operation INT,
                        founder_name VARCHAR(255),
                        website VARCHAR(512),
                        founder_title VARCHAR(255),
                        list_building_filters TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # Users table: only user fields + company_id (company name lives in company table, joined when needed)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        first_name VARCHAR(255),
                        last_name VARCHAR(255),
                        email VARCHAR(255) UNIQUE NOT NULL,
                        password VARCHAR(255),
                        job_title VARCHAR(255),
                        company_id INT NULL,
                        is_primary TINYINT(1) DEFAULT 0,
                        is_active TINYINT(1) DEFAULT 1,
                        auth_provider VARCHAR(50),
                        auth_provider_id VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # Subscription plan catalog. subscription_id 0=basic, 1=success, 2=premium; >2 = custom. First 3 must never be changed.
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS subscription_plan (
                        subscription_id INT PRIMARY KEY,
                        plan_name VARCHAR(50) NOT NULL,
                        monthly_cost DECIMAL(10, 2) NOT NULL DEFAULT 0,
                        annual_cost DECIMAL(10, 2) NOT NULL DEFAULT 0,
                        member_count INT NOT NULL DEFAULT 1,
                        is_system TINYINT(1) NOT NULL DEFAULT 0
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                # Seed default plans (subscription_id 0, 1, 2). Do not modify these rows.
                cursor.execute("SELECT COUNT(*) AS n FROM subscription_plan")
                if cursor.fetchone()["n"] == 0:
                    cursor.execute("""
                        INSERT INTO subscription_plan (subscription_id, plan_name, monthly_cost, annual_cost, member_count, is_system)
                        VALUES
                        (0, 'basic', 0, 0, 1, 1),
                        (1, 'success', 59, 708, 3, 1),
                        (2, 'premium', 99, 1188, 5, 1)
                    """)
                    connection.commit()

                # Company subscription: which plan a company is on (maps company_id -> subscription_id)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS company_subscription (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        company_id INT NOT NULL UNIQUE,
                        subscription_id INT NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'active',
                        started_at TIMESTAMP NULL,
                        ends_at TIMESTAMP NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE,
                        FOREIGN KEY (subscription_id) REFERENCES subscription_plan(subscription_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # Company payment methods: safely stored card metadata (no full PAN/CVC)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS company_payment_method (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        company_id INT NOT NULL,
                        brand VARCHAR(32) NOT NULL,
                        last4 VARCHAR(4) NOT NULL,
                        expiry_month TINYINT NULL,
                        expiry_year SMALLINT NULL,
                        is_default TINYINT(1) NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        deleted_at TIMESTAMP NULL,
                        FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # Invoices / billing history (transaction status assumed succeeded until gateway)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS company_invoice (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        company_id INT NOT NULL,
                        subscription_id INT NOT NULL,
                        plan_name VARCHAR(100) NOT NULL,
                        amount DECIMAL(10, 2) NOT NULL,
                        currency VARCHAR(3) NOT NULL DEFAULT 'USD',
                        status VARCHAR(32) NOT NULL DEFAULT 'succeeded',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE,
                        FOREIGN KEY (subscription_id) REFERENCES subscription_plan(subscription_id)
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
                        funding_for VARCHAR(255),
                        location VARCHAR(255),
                        eligibility TEXT,
                        url VARCHAR(2048),
                        status VARCHAR(50) DEFAULT 'Open',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # Company grants: shared saved grants and applications for all users in the company
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS company_grants (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        company_id INT NOT NULL,
                        grant_id INT NOT NULL,
                        year INT NOT NULL,
                        quarter INT NOT NULL,
                        status VARCHAR(50) DEFAULT 'Saved',
                        applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        notes TEXT,
                        FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE,
                        FOREIGN KEY (grant_id) REFERENCES grants(id),
                        UNIQUE(company_id, grant_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # Seed sample grants if table is empty
                cursor.execute("SELECT COUNT(*) AS n FROM grants")
                if cursor.fetchone()["n"] == 0:
                    _seed_sample_grants(cursor)
                    connection.commit()

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

                # Company contacts: organization, contact name, email, phone, role; category = one of the fixed contact categories
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS company_contact (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        company_id INT NOT NULL,
                        category VARCHAR(100) NOT NULL,
                        organization VARCHAR(255),
                        contact_name VARCHAR(255),
                        email VARCHAR(255),
                        phone VARCHAR(64),
                        role VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # User-requested grants (admin can review/accept later)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS requested_grants (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        company_id INT NOT NULL,
                        user_id INT,
                        funding_organization VARCHAR(255) NOT NULL,
                        program_name VARCHAR(255) NOT NULL,
                        funding_description TEXT,
                        link_to_grant VARCHAR(2048) NOT NULL,
                        status VARCHAR(50) DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # Grant messages (message board per company grant)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS grant_messages (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        company_id INT NOT NULL,
                        grant_id INT NOT NULL,
                        user_id INT NULL,
                        message TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE,
                        FOREIGN KEY (grant_id) REFERENCES grants(id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # Migrate legacy status: Added -> Saved
                cursor.execute("UPDATE company_grants SET status = 'Saved' WHERE status = 'Added'")
                connection.commit()
        finally:
            connection.close()

    @staticmethod
    def create_user(first_name, last_name, email, password_hash):
        """Create a new user (sign up with email/password). Caller must set company_id via create_company_for_user(user_id, company_name=...) so the user is always mapped to a company."""
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (first_name, last_name, email, password)
                    VALUES (%s, %s, %s, %s)
                """, ((first_name or "").strip() or None, (last_name or "").strip() or None, email, password_hash))
                connection.commit()
                return cursor.lastrowid
        finally:
            connection.close()

    @staticmethod
    def get_user_by_email(email):
        """Get user by email."""
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                return cursor.fetchone()
        finally:
            connection.close()

    @staticmethod
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

    @staticmethod
    def create_oauth_user(email, name, provider, provider_id):
        """Create user from OAuth. Company name is stored only in the company table via create_company_for_user(user_id, company_name=...)."""
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (first_name, last_name, email, password, auth_provider, auth_provider_id)
                    VALUES (%s, NULL, %s, NULL, %s, %s)
                """, ((name or "").strip() or None, email, provider, provider_id))
                connection.commit()
                return cursor.lastrowid
        finally:
            connection.close()

    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID."""
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                return cursor.fetchone()
        finally:
            connection.close()

    @staticmethod
    def get_user_with_company(user_id):
        """Get user by ID with company name from company table (users JOIN company). Use this when company name must come from company, not users.company_name."""
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT u.*, c.company_name AS company_name
                       FROM users u
                       LEFT JOIN company c ON u.company_id = c.id
                       WHERE u.id = %s""",
                    (user_id,),
                )
                return cursor.fetchone()
        finally:
            connection.close()

    @staticmethod
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

    @staticmethod
    def update_user_profile(user_id):
        """Update user profile (reserved for legacy route). Prefer update_user_personal_info."""
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                connection.commit()
                return 1
        finally:
            connection.close()

    @staticmethod
    def update_user_personal_info(user_id, first_name=None, last_name=None, email=None, job_title=None):
        """Update user personal info. None means do not change."""
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                updates = []
                args = []
                if first_name is not None:
                    updates.append("first_name = %s")
                    args.append(first_name)
                if last_name is not None:
                    updates.append("last_name = %s")
                    args.append(last_name)
                if email is not None:
                    updates.append("email = %s")
                    args.append(email)
                if job_title is not None:
                    updates.append("job_title = %s")
                    args.append(job_title)
                if not updates:
                    return 0
                args.append(user_id)
                cursor.execute(
                    "UPDATE users SET " + ", ".join(updates) + " WHERE id = %s",
                    args,
                )
                connection.commit()
                return cursor.rowcount
        finally:
            connection.close()

    @staticmethod
    def get_company_by_id(company_id):
        """Get company by ID. Returns None if not found."""
        if not company_id:
            return None
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM company WHERE id = %s", (company_id,))
                return cursor.fetchone()
        finally:
            connection.close()

    @staticmethod
    def get_company_for_user(user_id):
        """Get company for user (via user's company_id). Returns None if user has no company."""
        user = Database.get_user_by_id(user_id)
        if not user or not user.get("company_id"):
            return None
        return Database.get_company_by_id(user["company_id"])

    @staticmethod
    def create_company_for_user(user_id, company_name=None):
        """Create a new company, assign basic plan, set user's company_id and is_primary=1. Every user must have company_id set.
        On signup, company_name is mandatory (caller must pass a non-empty name). When creating on the fly (e.g. get_current_company with create_if_missing), company_name may be omitted or empty.
        Basic plan: started_at = signup timestamp, ends_at = 7 days from signup. Returns the new company row."""
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO company (company_name) VALUES (%s)",
                    ((company_name or "").strip() or "",),
                )
                connection.commit()
                company_id = cursor.lastrowid
                cursor.execute(
                    """INSERT INTO company_subscription (company_id, subscription_id, status, started_at, ends_at)
                       VALUES (%s, %s, 'active', CURRENT_TIMESTAMP, IF(%s = 0, TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 7 DAY)), NULL))""",
                    (company_id, Database.SUBSCRIPTION_ID_BASIC, Database.SUBSCRIPTION_ID_BASIC),
                )
                connection.commit()
                cursor.execute(
                    "UPDATE users SET company_id = %s, is_primary = 1 WHERE id = %s",
                    (company_id, user_id),
                )
                connection.commit()
                return Database.get_company_by_id(company_id)
        finally:
            connection.close()

    @staticmethod
    def get_current_company(user_id, create_if_missing=False):
        """Get company row for the given user. If create_if_missing=True, create a company when missing.
        Returns company dict or None. All database access for 'current user company' lives here."""
        if not user_id:
            return None
        company = Database.get_company_for_user(user_id)
        if company:
            return company
        if create_if_missing:
            return Database.create_company_for_user(user_id, company_name="")
        return None

    @staticmethod
    def get_current_company_id(user_id, create_if_missing=False):
        """Get company_id for the given user. If create_if_missing=True, create a company when missing.
        Returns company id or None. Delegates to get_current_company."""
        company = Database.get_current_company(user_id, create_if_missing=create_if_missing)
        return company["id"] if company else None

    @staticmethod
    def get_company_subscription(company_id):
        """Get the subscription row for a company (join with subscription_plan). Returns None if no subscription."""
        if not company_id:
            return None
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT cs.id, cs.company_id, cs.subscription_id, cs.status, cs.started_at, cs.ends_at,
                              sp.plan_name, sp.monthly_cost, sp.annual_cost, sp.member_count
                       FROM company_subscription cs
                       JOIN subscription_plan sp ON sp.subscription_id = cs.subscription_id
                       WHERE cs.company_id = %s
                       ORDER BY cs.id DESC LIMIT 1""",
                    (company_id,),
                )
                return cursor.fetchone()
        finally:
            connection.close()

    @staticmethod
    def get_subscription_max_members(company_id):
        """Return max team members for the company's subscription (from subscription_plan.member_count)."""
        sub = Database.get_company_subscription(company_id)
        if sub and sub.get("member_count") is not None:
            return int(sub["member_count"])
        return 1

    @staticmethod
    def get_subscription_plan_name(company_id):
        """Return plan name for the company's subscription (from subscription_plan.plan_name)."""
        sub = Database.get_company_subscription(company_id)
        if sub and sub.get("plan_name"):
            return (sub["plan_name"] or "basic").strip().lower()
        return "basic"

    @staticmethod
    def subscription_can_start_grants(company_id):
        """Return True if the company's subscription allows starting new grants (trial still active or paid plan). False if trial ended (ends_at in the past)."""
        sub = Database.get_company_subscription(company_id)
        if not sub:
            return False
        ends_at = sub.get("ends_at")
        if ends_at is None:
            return True
        try:
            return ends_at > datetime.now()
        except (TypeError, ValueError):
            return True

    @staticmethod
    def get_trial_status(company_id):
        """Return dict: days_left (int or None), ended (bool). For display when subscription has ends_at (e.g. basic trial)."""
        sub = Database.get_company_subscription(company_id)
        if not sub:
            return {"days_left": None, "ended": False}
        ends_at = sub.get("ends_at")
        if ends_at is None:
            return {"days_left": None, "ended": False}
        try:
            now = datetime.now()
            if hasattr(ends_at, "__le__"):
                end_dt = ends_at
            else:
                end_dt = datetime.fromisoformat(str(ends_at).replace("Z", "+00:00")) if isinstance(ends_at, str) else now
            if end_dt <= now:
                return {"days_left": None, "ended": True}
            delta = end_dt - now
            return {"days_left": max(0, delta.days), "ended": False}
        except (TypeError, ValueError):
            return {"days_left": None, "ended": False}

    @staticmethod
    def get_subscription_banner_status(company_id):
        """Return dict: banner_type ('trial'|'trial_ended'|'welcome'|'expiring_soon'|'expired'), days_left (int or None).
        Basic plan (subscription_id 0): trial days or trial_ended. Paid (plan > 0): welcome only if not expiring; else expiring_soon or expired.
        """
        sub = Database.get_company_subscription(company_id)
        if not sub:
            return {"banner_type": "welcome", "days_left": None}
        plan_id = sub.get("subscription_id")
        if plan_id is None:
            return {"banner_type": "welcome", "days_left": None}
        plan_id = int(plan_id)
        ends_at = sub.get("ends_at")
        now = datetime.now()

        def parse_end_dt():
            if ends_at is None:
                return None
            if hasattr(ends_at, "__le__"):
                return ends_at
            if isinstance(ends_at, str):
                return datetime.fromisoformat(ends_at.replace("Z", "+00:00"))
            return None

        end_dt = parse_end_dt()

        if plan_id == 0:
            if end_dt is None:
                return {"banner_type": "welcome", "days_left": None}
            if end_dt <= now:
                return {"banner_type": "trial_ended", "days_left": None}
            return {"banner_type": "trial", "days_left": max(0, (end_dt - now).days)}

        if end_dt is None:
            return {"banner_type": "welcome", "days_left": None}
        if end_dt <= now:
            return {"banner_type": "expired", "days_left": None}
        days_left = (end_dt - now).days
        if days_left <= 30:
            return {"banner_type": "expiring_soon", "days_left": days_left}
        return {"banner_type": "welcome", "days_left": None}

    @staticmethod
    def update_company_subscription(company_id, subscription_id=None, status=None):
        """Update company's subscription. subscription_id: which plan (0=basic, 1=success, 2=premium, >2 custom). Creates row if missing. System plans 0,1,2 cannot be modified in subscription_plan; only the company's link can change."""
        sub = Database.get_company_subscription(company_id)
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                if not sub:
                    sub_id = subscription_id if subscription_id is not None else Database.SUBSCRIPTION_ID_BASIC
                    cursor.execute(
                        """INSERT INTO company_subscription (company_id, subscription_id, status, started_at, ends_at)
                           VALUES (%s, %s, %s, CURRENT_TIMESTAMP, IF(%s = 0, TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 7 DAY)), NULL))""",
                        (company_id, sub_id, status or "active", sub_id),
                    )
                else:
                    updates, args = [], []
                    if subscription_id is not None:
                        updates.append("subscription_id = %s")
                        args.append(subscription_id)
                        if int(subscription_id) != 0:
                            # Paid plans: next billing date = one year later only if default payment method is set (annual billing)
                            cursor.execute(
                                "SELECT 1 FROM company_payment_method WHERE company_id = %s AND is_default = 1 AND deleted_at IS NULL LIMIT 1",
                                (company_id,),
                            )
                            if cursor.fetchone():
                                updates.append("ends_at = TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 1 YEAR))")
                            else:
                                updates.append("ends_at = NULL")
                    if status is not None:
                        updates.append("status = %s")
                        args.append(status)
                    if updates:
                        args.append(company_id)
                        cursor.execute(
                            "UPDATE company_subscription SET " + ", ".join(updates) + " WHERE company_id = %s",
                            args,
                        )
                connection.commit()
        finally:
            connection.close()

    @staticmethod
    def get_plan_by_id(subscription_id):
        """Return subscription_plan row for the given subscription_id. None if not found."""
        if subscription_id is None:
            return None
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT subscription_id, plan_name, monthly_cost, annual_cost, member_count, is_system FROM subscription_plan WHERE subscription_id = %s",
                    (subscription_id,),
                )
                return cursor.fetchone()
        finally:
            connection.close()

    @staticmethod
    def get_plan_max_members(subscription_id):
        """Return member_count for the given subscription_id. Default 1 if unknown."""
        plan = Database.get_plan_by_id(subscription_id)
        return int(plan["member_count"]) if plan and plan.get("member_count") is not None else 1

    @staticmethod
    def get_company_members(company_id):
        """Return users in this company, primary first, then by name/email. Empty list if no company."""
        if not company_id:
            return []
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT id, first_name, last_name, email, job_title, is_primary, is_active
                       FROM users WHERE company_id = %s
                       ORDER BY is_primary DESC, COALESCE(first_name, last_name, email) ASC, email ASC""",
                    (company_id,),
                )
                return cursor.fetchall()
        finally:
            connection.close()

    @staticmethod
    def add_payment_method(company_id, brand, last4, expiry_month=None, expiry_year=None, is_default=False):
        """Safely store a payment method for a company. Only stores brand, last4, and optional expiry (no PAN/CVC).
        If is_default and company is on a paid plan, sets next billing date to one year from now (annual billing)."""
        if not company_id or not brand or not last4:
            return None
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                # If setting as default, clear previous defaults
                if is_default:
                    cursor.execute(
                        "UPDATE company_payment_method SET is_default = 0 WHERE company_id = %s AND deleted_at IS NULL",
                        (company_id,),
                    )
                cursor.execute(
                    """
                    INSERT INTO company_payment_method (company_id, brand, last4, expiry_month, expiry_year, is_default)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (company_id, brand[:32], str(last4)[-4:], expiry_month, expiry_year, 1 if is_default else 0),
                )
                # Paid plans: next billing date = one year from now when default payment method is set (annual billing)
                if is_default:
                    sub = Database.get_company_subscription(company_id)
                    if sub and int(sub.get("subscription_id", 0)) not in (0, None):
                        cursor.execute(
                            "UPDATE company_subscription SET ends_at = TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 1 YEAR)) WHERE company_id = %s",
                            (company_id,),
                        )
                connection.commit()
                return cursor.lastrowid
        finally:
            connection.close()

    @staticmethod
    def get_payment_methods(company_id):
        """Return non-deleted payment methods for a company, newest first."""
        if not company_id:
            return []
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id AS payment_method_id, brand, last4, expiry_month, expiry_year, is_default, created_at
                    FROM company_payment_method
                    WHERE company_id = %s AND deleted_at IS NULL
                    ORDER BY is_default DESC, created_at DESC
                    """,
                    (company_id,),
                )
                return cursor.fetchall()
        finally:
            connection.close()

    @staticmethod
    def set_default_payment_method(company_id, method_id):
        """Set one payment method as default; clear default on all others for this company.
        For Success/Premium plans, sets next billing date to one year from now (annual billing)."""
        if not company_id or not method_id:
            return 0
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE company_payment_method SET is_default = 0 WHERE company_id = %s AND deleted_at IS NULL",
                    (company_id,),
                )
                cursor.execute(
                    """
                    UPDATE company_payment_method
                    SET is_default = 1
                    WHERE id = %s AND company_id = %s AND deleted_at IS NULL
                    """,
                    (method_id, company_id),
                )
                # Paid plans: next billing date = one year from now when default payment method is set (annual billing)
                sub = Database.get_company_subscription(company_id)
                if sub and int(sub.get("subscription_id", 0)) not in (0, None):
                    cursor.execute(
                        "UPDATE company_subscription SET ends_at = TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 1 YEAR)) WHERE company_id = %s",
                        (company_id,),
                    )
                connection.commit()
                return cursor.rowcount
        finally:
            connection.close()

    @staticmethod
    def clear_default_payment_method(company_id):
        """Clear default payment method for the company (no payment method will be default)."""
        if not company_id:
            return 0
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE company_payment_method SET is_default = 0 WHERE company_id = %s AND deleted_at IS NULL",
                    (company_id,),
                )
                connection.commit()
                return cursor.rowcount
        finally:
            connection.close()

    @staticmethod
    def remove_payment_method(company_id, method_id):
        """Soft-delete a payment method for a company."""
        if not company_id or not method_id:
            return 0
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE company_payment_method
                    SET deleted_at = CURRENT_TIMESTAMP, is_default = 0
                    WHERE id = %s AND company_id = %s AND deleted_at IS NULL
                    """,
                    (method_id, company_id),
                )
                connection.commit()
                return cursor.rowcount
        finally:
            connection.close()

    @staticmethod
    def add_invoice(company_id, subscription_id, plan_name, amount, currency="USD", status="succeeded"):
        """Record an invoice (transaction assumed succeeded until payment gateway)."""
        if not company_id or subscription_id is None or not plan_name or amount is None:
            return None
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO company_invoice (company_id, subscription_id, plan_name, amount, currency, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (company_id, subscription_id, plan_name, float(amount), currency, status or "succeeded"),
                )
                connection.commit()
                return cursor.lastrowid
        finally:
            connection.close()

    @staticmethod
    def get_billing_history(company_id):
        """Return billing history for dashboard: list of dicts with plan_name, date, amount (formatted)."""
        if not company_id:
            return []
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, plan_name, amount, currency, created_at
                    FROM company_invoice
                    WHERE company_id = %s
                    ORDER BY created_at DESC
                    """,
                    (company_id,),
                )
                rows = cursor.fetchall()
                out = []
                for r in rows:
                    dt = r.get("created_at")
                    if isinstance(dt, datetime):
                        date_str = dt.strftime("%b %d, %Y")
                    else:
                        date_str = str(dt)[:10] if dt else ""
                    amt = r.get("amount")
                    curr = (r.get("currency") or "USD").strip() or "USD"
                    if curr == "USD":
                        amount_str = "$%.2f" % (float(amt) if amt is not None else 0)
                    else:
                        amount_str = "%s %.2f" % (curr, float(amt) if amt is not None else 0)
                    out.append({
                        "invoice_id": r.get("id"),
                        "plan_name": r.get("plan_name") or "Plan",
                        "date": date_str,
                        "amount": amount_str,
                    })
                return out
        finally:
            connection.close()

    @staticmethod
    def get_last_invoice_amount_for_plan(company_id, subscription_id):
        """Return the amount of the most recent invoice for this company and plan, or None."""
        if not company_id or subscription_id is None:
            return None
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT amount FROM company_invoice
                    WHERE company_id = %s AND subscription_id = %s
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (company_id, subscription_id),
                )
                row = cursor.fetchone()
                return float(row["amount"]) if row and row.get("amount") is not None else None
        finally:
            connection.close()

    @staticmethod
    def set_user_active(user_id, is_active):
        """Set user is_active (1 or 0). Returns rowcount."""
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET is_active = %s WHERE id = %s",
                    (1 if is_active else 0, user_id),
                )
                connection.commit()
                return cursor.rowcount
        finally:
            connection.close()

    @staticmethod
    def add_team_member(company_id, first_name, last_name, email, job_title, password_hash=None):
        """
        Create a new user as team member. Use the logged-in user's company: pass company_id from get_current_company(session['user_id']).
        New user's company_id is set to this company so they see the same company data (grants, contacts, subscription, etc.).
        Every user must have company_id; for add-member we do not create a new company—we use the inviter's company_id.
        Sets is_primary=0, is_active=1. Returns new user id or None (e.g. duplicate email).
        """
        email = (email or "").strip()
        if not email:
            return None
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO users (first_name, last_name, email, password, job_title, company_id, is_primary, is_active)
                       VALUES (%s, %s, %s, %s, %s, %s, 0, 1)""",
                    (
                        (first_name or "").strip() or None,
                        (last_name or "").strip() or None,
                        email,
                        password_hash,
                        (job_title or "").strip() or None,
                        company_id,
                    ),
                )
                connection.commit()
                return cursor.lastrowid
        except pymysql.IntegrityError:
            connection.rollback()
            return None
        finally:
            connection.close()

    @staticmethod
    def update_company(company_id, **fields):
        """Update company by ID. Only updates provided fields (e.g. legal_entity_name=..., company_name=...)."""
        allowed = {
            "legal_entity_name", "operating_name", "company_name",
            "provincial_corporate_access_number", "workers_compensation_number", "business_number",
            "business_phone_number", "address", "date_of_incorporation", "postal_code",
            "years_in_operation", "founder_name", "website", "founder_title",
        }
        updates = []
        args = []
        for k, v in fields.items():
            if k in allowed:
                updates.append(f"{k} = %s")
                args.append(v)
        if not updates:
            return 0
        args.append(company_id)
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE company SET " + ", ".join(updates) + " WHERE id = %s",
                    args,
                )
                connection.commit()
                return cursor.rowcount
        finally:
            connection.close()

    @staticmethod
    def get_user_filter_settings(user_id):
        """Get saved List Building filter settings for the user's company. Returns {} if no company or invalid JSON."""
        company = Database.get_company_for_user(user_id)
        if not company or not company.get("list_building_filters"):
            return {}
        try:
            return json.loads(company["list_building_filters"]) or {}
        except (TypeError, ValueError):
            return {}

    # Password reset
    @staticmethod
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def save_user_filter_settings(user_id, filters_dict):
        """Save List Building filter settings for the user's company. filters_dict should be JSON-serializable. Returns 0 if user has no company."""
        company = Database.get_company_for_user(user_id)
        if not company:
            return 0
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE company SET list_building_filters = %s WHERE id = %s",
                    (json.dumps(filters_dict or {}), company["id"]),
                )
                connection.commit()
                return cursor.rowcount
        finally:
            connection.close()

    @staticmethod
    def get_all_grants():
        """Get all grants."""
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM grants")
                return cursor.fetchall()
        finally:
            connection.close()

    @staticmethod
    def get_grant_by_id(grant_id):
        """Get grant by ID."""
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM grants WHERE id = %s", (grant_id,))
                return cursor.fetchone()
        finally:
            connection.close()

    # --- Company grants (shared for all users in the company) ---

    @staticmethod
    def get_company_grants(company_id):
        """Get grants saved for the company (shared by all users). Returns list with status, applied_date, notes, year, quarter."""
        if not company_id:
            return []
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT g.*, cg.status, cg.applied_date, cg.notes, cg.year, cg.quarter FROM company_grants cg JOIN grants g ON cg.grant_id = g.id WHERE cg.company_id = %s ORDER BY cg.applied_date DESC",
                    (company_id,),
                )
                return cursor.fetchall()
        finally:
            connection.close()

    @staticmethod
    def get_company_grant(company_id, grant_id):
        """Get a single company grant (grant + status) or None."""
        if not company_id or not grant_id:
            return None
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT g.*, cg.status, cg.applied_date, cg.notes, cg.year, cg.quarter FROM company_grants cg JOIN grants g ON cg.grant_id = g.id WHERE cg.company_id = %s AND cg.grant_id = %s LIMIT 1",
                    (company_id, grant_id),
                )
                return cursor.fetchone()
        finally:
            connection.close()

    @staticmethod
    def get_grant_messages(company_id, grant_id):
        """Get messages for a company grant, with user first_name. Order by created_at asc."""
        if not company_id or not grant_id:
            return []
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT gm.id, gm.user_id, gm.message, gm.created_at,
                              u.first_name, u.last_name
                       FROM grant_messages gm
                       LEFT JOIN users u ON u.id = gm.user_id
                       WHERE gm.company_id = %s AND gm.grant_id = %s
                       ORDER BY gm.created_at ASC""",
                    (company_id, grant_id),
                )
                return cursor.fetchall()
        finally:
            connection.close()

    @staticmethod
    def add_grant_message(company_id, grant_id, user_id, message):
        """Add a message to the grant message board. Returns new id or None."""
        if not company_id or not grant_id or not (message or "").strip():
            return None
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO grant_messages (company_id, grant_id, user_id, message) VALUES (%s, %s, %s, %s)",
                    (company_id, grant_id, user_id or None, (message or "").strip()),
                )
                connection.commit()
                return cursor.lastrowid
        finally:
            connection.close()

    @staticmethod
    def apply_for_grant_company(company_id, grant_id):
        """Apply for a grant on behalf of the company (insert/update in company_grants)."""
        if not company_id:
            return None
        year, quarter = Utils.current_year_quarter()
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO company_grants (company_id, grant_id, year, quarter, status)
                    VALUES (%s, %s, %s, %s, 'Applied')
                    ON DUPLICATE KEY UPDATE status = 'Applied', year = %s, quarter = %s, applied_date = CURRENT_TIMESTAMP
                """, (company_id, grant_id, year, quarter, year, quarter))
                connection.commit()
                return cursor.lastrowid if cursor.lastrowid else True
        finally:
            connection.close()

    @staticmethod
    def add_grant_to_portfolio_company(company_id, grant_id, quarter_str):
        """Save a grant for the company with planned quarter (List Building star/save)."""
        if not company_id:
            return None
        year, quarter = Utils.parse_quarter_string(quarter_str)
        if year is None or quarter is None:
            raise ValueError("Invalid quarter; expected e.g. '2026 Q2'")
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO company_grants (company_id, grant_id, year, quarter, status)
                    VALUES (%s, %s, %s, %s, 'Saved')
                    ON DUPLICATE KEY UPDATE year = %s, quarter = %s, status = 'Saved', applied_date = CURRENT_TIMESTAMP
                """, (company_id, grant_id, year, quarter, year, quarter))
                connection.commit()
                return cursor.lastrowid if cursor.lastrowid else True
        finally:
            connection.close()

    @staticmethod
    def update_grant_status_company(company_id, grant_id, status):
        """Update grant application status for the company."""
        if not company_id:
            return 0
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE company_grants SET status = %s WHERE company_id = %s AND grant_id = %s", (status, company_id, grant_id))
                connection.commit()
                return cursor.rowcount
        finally:
            connection.close()

    @staticmethod
    def remove_grant_from_portfolio_company(company_id, grant_id):
        """Remove a saved grant from the company's portfolio."""
        if not company_id:
            return 0
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM company_grants WHERE company_id = %s AND grant_id = %s", (company_id, grant_id))
                connection.commit()
                return cursor.rowcount
        finally:
            connection.close()

    # --- Company contacts (Contacts tab) ---
    CONTACT_CATEGORIES = [
        "Grant Advisors",
        "Bank / Loan Contact",
        "Investors",
        "SR & ED Advisors",
        "Grant Consultants / Writers",
        "Other Contacts",
    ]

    @staticmethod
    def get_contacts(company_id, category=None, search=None):
        """Get contacts for a company. category=None means all; search filters by organization, contact_name, email, phone, role."""
        if not company_id:
            return []
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM company_contact WHERE company_id = %s"
                args = [company_id]
                if category:
                    sql += " AND category = %s"
                    args.append(category)
                if search and search.strip():
                    q = "%" + search.strip().replace("%", "\\%").replace("_", "\\_") + "%"
                    sql += " AND (organization LIKE %s OR contact_name LIKE %s OR email LIKE %s OR phone LIKE %s OR role LIKE %s)"
                    args.extend([q] * 5)
                sql += " ORDER BY category, contact_name"
                cursor.execute(sql, args)
                return cursor.fetchall()
        finally:
            connection.close()

    @staticmethod
    def get_contacts_for_user(user_id, category=None, search=None):
        """Get contacts for the user's company via explicit join: users (user_id) -> company_id -> company_contact.
        Ensures we always read contacts for the company linked to the user."""
        if not user_id:
            return []
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                sql = """SELECT cc.* FROM company_contact cc
                         INNER JOIN users u ON u.company_id = cc.company_id
                         WHERE u.id = %s"""
                args = [user_id]
                if category:
                    sql += " AND cc.category = %s"
                    args.append(category)
                if search and search.strip():
                    q = "%" + search.strip().replace("%", "\\%").replace("_", "\\_") + "%"
                    sql += " AND (cc.organization LIKE %s OR cc.contact_name LIKE %s OR cc.email LIKE %s OR cc.phone LIKE %s OR cc.role LIKE %s)"
                    args.extend([q] * 5)
                sql += " ORDER BY cc.category, cc.contact_name"
                cursor.execute(sql, args)
                return cursor.fetchall()
        finally:
            connection.close()

    @staticmethod
    def get_contact_category_counts_for_user(user_id):
        """Return dict of category -> count for the user's company contacts (join: users -> company_contact)."""
        if not user_id:
            return {c: 0 for c in Database.CONTACT_CATEGORIES}
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT cc.category, COUNT(*) AS cnt FROM company_contact cc
                       INNER JOIN users u ON u.company_id = cc.company_id
                       WHERE u.id = %s GROUP BY cc.category""",
                    (user_id,),
                )
                rows = cursor.fetchall()
            counts = {c: 0 for c in Database.CONTACT_CATEGORIES}
            for r in rows:
                if r["category"] in counts:
                    counts[r["category"]] = r["cnt"]
            return counts
        finally:
            connection.close()

    @staticmethod
    def get_contact_category_counts(company_id):
        """Return dict of category -> count for company contacts."""
        if not company_id:
            return {c: 0 for c in Database.CONTACT_CATEGORIES}
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT category, COUNT(*) AS cnt FROM company_contact WHERE company_id = %s GROUP BY category",
                    (company_id,),
                )
                rows = cursor.fetchall()
            counts = {c: 0 for c in Database.CONTACT_CATEGORIES}
            for r in rows:
                if r["category"] in counts:
                    counts[r["category"]] = r["cnt"]
            return counts
        finally:
            connection.close()

    @staticmethod
    def get_contact_by_id(contact_id, company_id):
        """Get a single contact by id; must belong to company_id."""
        if not company_id or not contact_id:
            return None
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM company_contact WHERE id = %s AND company_id = %s",
                    (contact_id, company_id),
                )
                return cursor.fetchone()
        finally:
            connection.close()

    @staticmethod
    def create_contact(company_id, category, organization=None, contact_name=None, email=None, phone=None, role=None):
        """Create a contact for the company. category must be one of CONTACT_CATEGORIES."""
        if not company_id or category not in Database.CONTACT_CATEGORIES:
            return None
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO company_contact (company_id, category, organization, contact_name, email, phone, role)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        company_id,
                        category,
                        (organization or "").strip() or None,
                        (contact_name or "").strip() or None,
                        (email or "").strip() or None,
                        (phone or "").strip() or None,
                        (role or "").strip() or None,
                    ),
                )
                connection.commit()
                return cursor.lastrowid
        finally:
            connection.close()

    @staticmethod
    def update_contact(contact_id, company_id, category=None, organization=None, contact_name=None, email=None, phone=None, role=None):
        """Update a contact. Only provided fields are updated. Returns rowcount."""
        if not company_id or not contact_id:
            return 0
        if category is not None and category not in Database.CONTACT_CATEGORIES:
            return 0
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                updates = []
                args = []
                if category is not None:
                    updates.append("category = %s")
                    args.append(category)
                if organization is not None:
                    updates.append("organization = %s")
                    args.append((organization or "").strip() or None)
                if contact_name is not None:
                    updates.append("contact_name = %s")
                    args.append((contact_name or "").strip() or None)
                if email is not None:
                    updates.append("email = %s")
                    args.append((email or "").strip() or None)
                if phone is not None:
                    updates.append("phone = %s")
                    args.append((phone or "").strip() or None)
                if role is not None:
                    updates.append("role = %s")
                    args.append((role or "").strip() or None)
                if not updates:
                    return 0
                args.extend([contact_id, company_id])
                cursor.execute(
                    "UPDATE company_contact SET " + ", ".join(updates) + " WHERE id = %s AND company_id = %s",
                    args,
                )
                connection.commit()
                return cursor.rowcount
        finally:
            connection.close()

    @staticmethod
    def delete_contact(contact_id, company_id):
        """Delete a contact. Returns rowcount."""
        if not company_id or not contact_id:
            return 0
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM company_contact WHERE id = %s AND company_id = %s", (contact_id, company_id))
                connection.commit()
                return cursor.rowcount
        finally:
            connection.close()

    @staticmethod
    def create_requested_grant(company_id, user_id, funding_organization, program_name, funding_description, link_to_grant):
        """Insert a user-requested grant for admin review. Returns new id or None."""
        if not company_id or not (funding_organization or "").strip() or not (program_name or "").strip() or not (link_to_grant or "").strip():
            return None
        connection = get_db()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO requested_grants (company_id, user_id, funding_organization, program_name, funding_description, link_to_grant)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (
                        company_id,
                        user_id or None,
                        (funding_organization or "").strip(),
                        (program_name or "").strip(),
                        (funding_description or "").strip() or None,
                        (link_to_grant or "").strip(),
                    ),
                )
                connection.commit()
                return cursor.lastrowid
        finally:
            connection.close()
