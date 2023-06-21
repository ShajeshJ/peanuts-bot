venv_dir := .venv
venv_activate := . $(venv_dir)/bin/activate

check_poetry:
	@poetry >/dev/null 2>&1 || (echo "poetry must be installed first"; exit 1)

create_env_file:
	touch .env

create_venv:
	python -m venv $(venv_dir)

poetry_install:
	poetry install

init: check_poetry create_env_file create_venv poetry_install

run:
	$(venv_activate) && python app.py
