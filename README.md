# peanuts-bot
discord bot for a private server, written in python

## Pinning new dependencies to requirements files
1. Make sure your venv packages have all packages already pinned in the existing requirements files (i.e. `make pip_install`)
2. Run `make list_dep_diff` and make sure there is no diff output
3. Activate your venv and install the new package with pip
4. Run `make list_dep_diff` again. You should now see a diff, containing your package and any transitive package updates
5. Ensure each package listed is pinned appropriate in either the regular or the dev requirement files.
