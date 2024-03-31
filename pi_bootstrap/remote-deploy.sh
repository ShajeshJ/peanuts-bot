if [[ -z "${START_DIR}" ]]; then echo "Please set the START_DIR env variable"; exit 1; fi
cd ${START_DIR}
git pull

poetry_cmd="poetry"
if ! command -v "$poetry_cmd"; then
    poetry_cmd=$(~/.asdf/bin/asdf which poetry)
fi

source .venv/bin/activate
eval "$poetry_cmd install --only main --sync"
sudo make pi_install
