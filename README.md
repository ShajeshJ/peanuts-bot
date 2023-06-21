# peanuts-bot
discord bot for a private server, written in python ([version here](.tool-versions)) using [interactions-py](https://github.com/interactions-py/interactions.py)

## Initializing the repo
> **Note**:
> [asdf](https://asdf-vm.com) tool versioning is supported
1. Ensure you have [python](https://www.python.org) and [poetry](https://python-poetry.org) installed ([versions listed here](.tool-versions))
1. Run `make init` to initalize your venv
1. Run `make run` to boot up the service.
1. During the first boot ups, you may see errors like `KeyError: Missing required env var ""`
    - To fix this, specify an appropriate value for the missing variable in the `.env` file
    - A complete list of configurable environment variables can be found in [config.py](peanuts_bot/config.py)

## Pinning new dependencies
To add new packages, use `poetry add <package>==<version>`
> **Warning**:
> For non-prod dependencies, use the `--group` option (e.g. `poetry add --group=dev <dev-package>==<version>`)

## Troubleshooting
- poetry says `poetry.lock` and `pyproject.toml` don't match
    - Assuming the dependencies in [pyproject.toml](pyproject.toml) are correct, just run `poetry lock --no-update` and commit the changes
