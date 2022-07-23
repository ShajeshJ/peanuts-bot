venv_dir := .venv
venv_activate := . $(venv_dir)/bin/activate
req_file := requirements.txt
dev_req_file := requirements-dev.txt

init:
	python -m venv $(venv_dir) && \
	$(venv_activate) && \
	pip install -r $(req_file) -r $(dev_req_file)

list_dep_diff:
	@-$(venv_activate) && \
	bash -c 'diff -d --color=always <(cat $(req_file) $(dev_req_file) | sort) <(pip freeze)'
	@printf "\n\033[32mDeps > need to be added to one of the requirements files\033[0m\n"
	@printf "\033[31mDeps < need to be installed to your virtual env\033[0m"

run:
	$(venv_activate) && python app.py
