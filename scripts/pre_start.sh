alembic revision --autogenerate

alembic upgrade head

python3 ./scripts/init_data.py
