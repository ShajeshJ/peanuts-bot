venv_dir := .venv
venv_activate := . $(venv_dir)/bin/activate
lines := 50

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
	-sudo systemctl stop peanutsbot
	sudo CWD=$$(pwd) envsubst < pi_bootstrap/peanutsbot.service > /etc/systemd/system/peanutsbot.service
	sudo systemctl daemon-reload
	sudo systemctl enable peanutsbot
	sudo systemctl start peanutsbot

pi_status:
	sudo systemctl status peanutsbot

pi_logs:
	sudo journalctl -u peanutsbot -f -n $(lines)
