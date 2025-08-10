import ssl
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from core.conf import settings  # import config từ pydantic_settings
from database.base import Base

# Đọc config từ alembic.ini
config = context.config

# Cấu hình logging từ file alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata để Alembic autogenerate
target_metadata = Base.metadata

# Lấy URL từ settings (pydantic_settings)
DATABASE_URL = settings.MYSQL_URL

# Convert từ async URL -> sync URL cho Alembic
if DATABASE_URL.startswith("mysql+asyncmy"):
    DATABASE_URL = DATABASE_URL.replace("mysql+asyncmy", "mysql+pymysql")

print(f"Using database URL: {DATABASE_URL}")

# Set URL vào config của Alembic
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# SSL config cho MySQL
connect_args = {}
if DATABASE_URL.startswith("mysql+pymysql"):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ssl_context


def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Chạy migration trực tiếp với DB."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# Gọi hàm tương ứng tùy theo mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
