venv_dir=.venv
venv_activate=. $(venv_dir)/bin/activate

init:
	python -m venv $(venv_dir) && \
	$(venv_activate) && \
	pip install -r requirements.txt -r requirements-dev.txt

run:
	$(venv_activate) && python app.py