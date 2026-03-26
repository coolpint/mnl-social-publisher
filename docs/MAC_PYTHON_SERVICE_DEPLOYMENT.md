# Mac Python Service Deployment

This is the lightweight Mac deployment for `mnl-social-publisher`.

Use this when:

- Docker Desktop feels too heavy
- the Mac stays on most of the time
- you are okay with a user-level `launchd` service that starts after login

This mode runs:

- a local Python virtualenv
- `gunicorn`
- a macOS `LaunchAgent`

## 1. Prepare the Mac

Install:

- Python 3.10 or newer
- Git

The remote Mac we tested already had:

```bash
/usr/local/bin/python3.13
```

Clone the repo to a stable path:

```bash
git clone git@github.com:coolpint/mnl-social-publisher.git
cd mnl-social-publisher
```

## 2. Create the env file

```bash
cp deploy/mnl-social-publisher.env.example deploy/mnl-social-publisher.env
```

Fill in:

- `MNL_ONEDRIVE_TENANT_ID`
- `MNL_ONEDRIVE_CLIENT_ID`
- `MNL_ONEDRIVE_CLIENT_SECRET`
- `MNL_ONEDRIVE_DRIVE_ID`
- `MNL_SOCIAL_WEB_BASIC_AUTH_USERNAME`
- `MNL_SOCIAL_WEB_BASIC_AUTH_PASSWORD`

Optional but recommended:

- `MNL_SOCIAL_PYTHON_BIN=/usr/local/bin/python3.13`
- `MNL_SOCIAL_VENV_DIR=/Users/<user>/codes/mnl-social-publisher/.venv-service`

The current service still respects:

- `PORT`
- `WEB_CONCURRENCY`
- `MNL_SOCIAL_BIND_HOST`
- all `MNL_SOCIAL_*_REMOTE_ROOT` settings

## 3. Build the Python environment

```bash
./scripts/mac_python_bootstrap.sh
```

This creates a virtualenv and installs the app plus `gunicorn`.

## 4. Install auto-start

```bash
./scripts/install_mac_python_launch_agent.sh
```

This installs a user-level `LaunchAgent` that runs:

```bash
./scripts/mac_python_service_run.sh
```

## 5. Verify it

```bash
curl -s http://127.0.0.1:8420/healthz
```

Expected response:

```text
ok
```

If `MNL_SOCIAL_BIND_HOST=0.0.0.0`, other devices on the same LAN can open:

```text
http://<mac-ip>:8420
```

## 6. Useful commands

```bash
./scripts/mac_python_bootstrap.sh
./scripts/install_mac_python_launch_agent.sh
./scripts/uninstall_mac_python_launch_agent.sh
launchctl kickstart -k "gui/$(id -u)/com.moneynlaw.social-publisher"
tail -f deploy/logs/python-service.out.log
tail -f deploy/logs/python-service.err.log
```

## Notes

- this is much lighter than Docker Desktop
- this is still a user `LaunchAgent`, so it starts after login
- if you want true boot-without-login behavior, the next step is a system `LaunchDaemon`
- after code or dependency updates, rerun `./scripts/mac_python_bootstrap.sh`
