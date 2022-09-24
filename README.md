# peanuts-bot
discord bot for a private server, written in python

## Initializing the repo
1. Run `make init` to initalize service dependencies
2. Run `make run` to boot up the service.
3. During the first boot ups, you may see errors like `KeyError: Missing required env var ""`
    - To fix this, specify an appropriate value for the missing variable in the `.env` file
    - A complete list of configurable environment variables can be found in `config.py`

## Pinning new dependencies to requirements files
1. Make sure your venv packages have all packages already pinned in the existing requirements files (i.e. `make pip_install`)
2. Run `make list_dep_diff` and make sure there is no diff output
3. Activate your venv and install the new package with pip
4. Run `make list_dep_diff` again. You should now see a diff, containing your package and any transitive package updates
5. Ensure each package listed is pinned appropriate in either the regular or the dev requirement files.
