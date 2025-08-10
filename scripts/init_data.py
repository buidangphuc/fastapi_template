import os

from common.log import log
from core.path_conf import INIT_DB_DIR
from database.db import AsyncSessionLocal


async def execute_sql_file(directory_path: str) -> None:
    """
    Execute all SQL files in a directory
    :param directory_path: Directory containing SQL files
    :return:
    """
    # Check if the path exists and is a directory
    if not os.path.isdir(directory_path):
        raise ValueError(f"Path {directory_path} is not a directory or does not exist")

    # Get all SQL files in the directory
    sql_files = [f for f in os.listdir(directory_path) if f.endswith(".sql")]

    # Sort files to ensure consistent execution order
    sql_files.sort()

    if not sql_files:
        log.warning(f"No SQL files found in {directory_path}")
        return

    log.info(f"Found {len(sql_files)} SQL files to execute")

    # Execute each SQL file
    async with AsyncSessionLocal() as session:
        for sql_file in sql_files:
            file_path = os.path.join(directory_path, sql_file)
            log.info(f"Executing SQL file: {sql_file}")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    sql = f.read()
                    await session.execute(sql)
                log.info(f"Successfully executed {sql_file}")
            except Exception as e:
                log.error(f"Error executing {sql_file}: {str(e)}")
                raise

        # Commit all changes at once after all files are executed
        await session.commit()


async def init_dev_data() -> None:
    """
    Initialize development test data
    :return:
    """
    # Initialize test data
    log.info("Inserting initial development data")
    try:
        await execute_sql_file(INIT_DB_DIR)
        log.info("Initial development data inserted")
    except Exception as e:
        log.error(f"Failed to insert development data: {str(e)}")
        raise
