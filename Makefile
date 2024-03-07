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

fix_lock:
	poetry lock --no-update

run:
	$(venv_activate) && python app.py

pi_install:
	@if ! [ "$(shell id -u)" = "0" ]; then echo "Please run using sudo"; exit 1; fi
	-systemctl stop peanutsbot
	CWD=$$(pwd) envsubst < pi_bootstrap/peanutsbot.service > /etc/systemd/system/peanutsbot.service
	systemctl daemon-reload
	systemctl enable peanutsbot
	systemctl start peanutsbot

pi_status:
	systemctl status peanutsbot

lines := 50
pi_logs:
	journalctl -u peanutsbot -f -n $(lines)
