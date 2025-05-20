from pathlib import Path


BASE_PATH = Path(__file__).resolve().parent.parent

# alembic migration files storage path
ALEMBIC_VERSION_DIR = BASE_PATH / 'alembic' / 'versions'

# log files path
LOG_DIR = BASE_PATH / 'log'

# static resources directory
STATIC_DIR = BASE_PATH / 'static'

# upload files directory
UPLOAD_DIR = STATIC_DIR / 'upload'

# offline IP database path
IP2REGION_XDB = STATIC_DIR / 'ip2region.xdb'

SSL_DIR = BASE_PATH/'ssl'

INIT_DB_DIR = BASE_PATH / 'sql' / 'mysql'

