from sqlalchemy import create_engine, text

# Database configuration
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:XLR8*xlr8&@localhost:5433/EmotionDB"

# Connect to PostgreSQL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

def add_missing_columns():
    columns_to_add = [
        ("profile_picture_url", "VARCHAR(500)"),
        ("is_verified", "BOOLEAN DEFAULT FALSE"),
        ("otp_secret", "VARCHAR(32)"),
        ("otp_enabled", "BOOLEAN DEFAULT FALSE"),
        ("otp_backup_codes", "TEXT"),
        ("temp_otp_secret", "VARCHAR(32)"),
        ("reset_token", "VARCHAR(64)"),
        ("reset_token_expires", "TIMESTAMP"),
        ("verification_token", "VARCHAR(64)"),
        ("verification_token_expires", "TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
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

                # Add the column
                conn.execute(text(f"""
                    ALTER TABLE users ADD COLUMN {column_name} {column_type}
                """))
                print(f"Successfully added '{column_name}' column to users table.")

    except Exception as e:
        print(f"Error adding columns: {e}")

if __name__ == "__main__":
    add_missing_columns()
