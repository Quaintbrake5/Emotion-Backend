from sqlalchemy import create_engine, text, Column, String, Boolean, Text, TIMESTAMP
from sqlalchemy.schema import Table

# Database configuration
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:XLR8*xlr8&@localhost:5433/EmotionDB"

# Connect to PostgreSQL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Define table metadata
from sqlalchemy import MetaData
metadata = MetaData()

def add_missing_columns():
    columns_to_add = [
        ("profile_picture_url", Column("profile_picture_url", String(500))),
        ("is_verified", Column("is_verified", Boolean, default=False)),
        ("otp_secret", Column("otp_secret", String(32))),
        ("otp_enabled", Column("otp_enabled", Boolean, default=False)),
        ("otp_backup_codes", Column("otp_backup_codes", Text)),
        ("temp_otp_secret", Column("temp_otp_secret", String(32))),
        ("reset_token", Column("reset_token", String(64))),
        ("reset_token_expires", Column("reset_token_expires", TIMESTAMP)),
        ("verification_token", Column("verification_token", String(64))),
        ("verification_token_expires", Column("verification_token_expires", TIMESTAMP)),
        ("updated_at", Column("updated_at", TIMESTAMP, default=text("CURRENT_TIMESTAMP")))
    ]

    try:
        with engine.begin() as conn:
            for column_name, column_type in columns_to_add:
                # Check if column exists
                result = conn.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name = :column_name
                """), {"column_name": column_name})

                if result.fetchone():
                    print(f"Column '{column_name}' already exists.")
                    continue

                # Add the column using SQLAlchemy Column object (safe from SQL injection)
                column = column_type
                conn.execute(text(f"""
                    ALTER TABLE users ADD COLUMN {column.name} {column.type.compile(dialect=conn.dialect)}
                """))
                print(f"Successfully added '{column_name}' column to users table.")

    except Exception as e:
        print(f"Error adding columns: {e}")

if __name__ == "__main__":
    add_missing_columns()
