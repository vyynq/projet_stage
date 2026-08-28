from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_email_verification_columns(engine: Engine):
    inspector = inspect(engine)
    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"

    statements = []
    if "email_verified_at" not in existing_columns:
        statements.append(f"ALTER TABLE users ADD COLUMN email_verified_at {datetime_type}")
    if "email_verification_code_hash" not in existing_columns:
        statements.append("ALTER TABLE users ADD COLUMN email_verification_code_hash VARCHAR")
    if "email_verification_expires_at" not in existing_columns:
        statements.append(f"ALTER TABLE users ADD COLUMN email_verification_expires_at {datetime_type}")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
