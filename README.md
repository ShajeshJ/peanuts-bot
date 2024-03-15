# peanuts-bot
discord bot for a private server, written in python ([version here](.tool-versions)) using [interactions-py](https://github.com/interactions-py/interactions.py)

## Initializing the repo
> [!TIP]
> [asdf](https://asdf-vm.com) tool versioning is supported
1. Ensure you have [python](https://www.python.org) and [poetry](https://python-poetry.org) installed ([versions listed here](.tool-versions))
1. Run `make init` to initalize your venv
1. Run `make run` to boot up the service.
1. During the first boot ups, you may see errors like `KeyError: Missing required env var ""`
    - To fix this, specify an appropriate value for the missing variable in the `.env` file
    - A complete list of configurable environment variables can be found in [config.py](peanuts_bot/config.py)

## Pinning new dependencies
To add new packages, use `poetry add <package>==<version>`
> [!WARNING]
> For non-prod dependencies, use the `--group` option (e.g. `poetry add --group=dev <dev-package>==<version>`)

## Troubleshooting
- poetry says `poetry.lock` and `pyproject.toml` don't match
    - Assuming the dependencies in [pyproject.toml](pyproject.toml) are correct, just run `poetry lock --no-update` and commit the changes

## Deployments
Currently, deployments can be triggered manually via SSH, and will run the bot as a _systemd_ service unit on the host machine.

> [!IMPORTANT]
> For the very initial deployment, you will need to manually pull down and [initialize the repo](#initializing-the-repo) on the host device.
These deploy steps will only work after the python app is runnable on the host device.

### Setup
1. Ensure your host device has SSH connections enabled.
1. Then add the following environment variables to your `.env` file
    - **`PI_HOST=`** : The SSH user+host to pass into the `ssh` command (should be of the format `{user}@{ip}`)
    - **`PI_START_DIR=`** : The top level directory of the bot folder on the host device
1. Finally, you can run `make remote_deploy` from your remote machine to trigger a new bot deploy on the host device.
