# Deployment Infrastructure

The bot runs as a systemd service on a Raspberry Pi, accessed via Tailscale. CI/CD is GitHub Actions.

---

## Full Deploy Flow

```
git push → main branch
  → GitHub Actions (.github/workflows/deploy.yml)
      → Tailscale OAuth connects runner to the Pi network
      → make remote_deploy ssh_cmd="tailscale ssh"
          → SSHes into Pi (SSH_HOST), runs pi_bootstrap/remote-deploy.sh:
              → git pull (origin/main)
              → poetry install --only main --sync
              → sudo make pi_install
                  → systemctl stop peanutsbot
                  → envsubst pi_bootstrap/peanutsbot.service → /etc/systemd/system/
                  → systemctl daemon-reload && enable && start
```

Trigger: any push to `main` that changes non-`.md` files.

---

## GitHub Actions Secrets & Variables

| Name | Type | Purpose |
|---|---|---|
| `TAILSCALE_OAUTH_CLIENT_ID` | Secret | Tailscale OAuth for runner |
| `TAILSCALE_OAUTH_CLIENT_SECRET` | Secret | Tailscale OAuth for runner |
| `SSH_HOST` | Secret | Pi's Tailscale hostname/IP |
| `START_DIR` | Variable | Absolute path to the repo on the Pi |

GitHub environment name: **`production`**.

---

## Makefile Targets

| Target | Purpose |
|---|---|
| `make init` | Create venv + install all deps (dev included) |
| `make run` | Run bot locally |
| `make remote_deploy` | SSH into Pi and run the deploy script. Requires `SSH_HOST` and `START_DIR` env vars. Locally, you must have Tailscale running and use `ssh_cmd="tailscale ssh"` if the Pi is only reachable over Tailscale. |
| `make pi_install` | Install/restart the systemd service (must run with sudo on the Pi) |
| `make pi_status` | `systemctl status peanutsbot` |
| `make pi_logs [lines=N]` | `journalctl -u peanutsbot -f -n <lines>` (default 50) |
| `make fix_lock` | `poetry lock --no-update` (update lock file without upgrading deps) |

---

## systemd Service (`pi_bootstrap/peanutsbot.service`)

- **User:** `pi`
- **ExecStart:** `pi_bootstrap/start-bot.sh` (activates venv, runs `python app.py`)
- **WorkingDirectory:** repo root (`$CWD`, substituted by `envsubst` during install)
- **Restart:** `always` with `RestartSec=120` (2-minute delay between restarts)
- **Dependency:** `After=network-online.target` — waits for network before starting

---

## Python & Dependency Management

- **Python:** 3.10.5, pinned via `.tool-versions` (asdf) and `pyproject.toml`
- **Package manager:** Poetry
- **CI installs:** `poetry install --only main --sync` (no dev deps on Pi)
- **Dev deps:** `ruff`, `mypy`, `types-python-dateutil`

---

## First-Time Pi Setup

Before the first automated deploy can work, the Pi needs the repo bootstrapped manually:
1. SSH into the Pi, clone the repo to `START_DIR`
2. Run `make init` (creates venv, installs all deps including dev)
3. Create a `.env` file with all required config values (see `config.py`)
4. After that, CI/CD handles all future deploys automatically

---

## Running Deploys Manually

```bash
SSH_HOST=<pi-tailscale-host> START_DIR=<repo-path-on-pi> make remote_deploy ssh_cmd="tailscale ssh"
```

Or SSH into the Pi directly and run `sudo make pi_install` after pulling changes.
