if [[ -z "${START_DIR}" ]]; then echo "Please set the START_DIR env variable"; exit 1; fi
cd ${START_DIR}
git pull
sudo make pi_install
