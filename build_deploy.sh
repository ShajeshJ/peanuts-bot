# This script assumes that the python version listed in .tool-versions is installed

poetry_version=$(cat .tool-versions | grep poetry | cut -d ' ' -f2)

if [ -z "$poetry_version" ]; then
  echo "poetry version not found"
  exit 1
fi

echo "installing poetry@$poetry_version"

python -m pip install "poetry==$poetry_version"

poetry install --only=main