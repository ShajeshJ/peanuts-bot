source .venv/bin/activate
poetry install --without dev --sync
python app.py
