# Mac Docker Deployment

This is the recommended first production-style deployment for `mnl-social-publisher`.

Use this approach when you have:

- a Mac that stays on most of the time
- Docker Desktop or OrbStack
- Tailscale on the same machine

The goal is:

- keep the app running through Docker
- make it restart automatically through `launchd`
- expose it only inside your Tailscale network

## 1. Prepare the Mac

Install:

- Docker Desktop or OrbStack
- Tailscale
- Git

Then put the repo on the Mac in a stable path, for example:

```bash
git clone git@github.com:coolpint/mnl-social-publisher.git
cd mnl-social-publisher
```

## 2. Create the env file

```bash
cp deploy/mnl-social-publisher.env.example deploy/mnl-social-publisher.env
```

Then fill in:

- `MNL_ONEDRIVE_TENANT_ID`
- `MNL_ONEDRIVE_CLIENT_ID`
- `MNL_ONEDRIVE_CLIENT_SECRET`
- `MNL_ONEDRIVE_DRIVE_ID`
- `MNL_SOCIAL_WEB_BASIC_AUTH_USERNAME`
- `MNL_SOCIAL_WEB_BASIC_AUTH_PASSWORD`

Choose how the web port should be exposed:

- `MNL_SOCIAL_BIND_HOST=127.0.0.1` keeps it local to the Mac only
- `MNL_SOCIAL_BIND_HOST=0.0.0.0` makes it reachable from the same LAN, for example `http://<mac-ip>:8420`

The default remote roots already point to:

- `social/inbox`
- `social/review`
- `social/approval`
- `social/outbox`
- `social/status`

The default image value is a local tag. `./scripts/mac_stack_up.sh` builds from the local Dockerfile, so a GHCR login is not required for the first deployment.

## 3. Start the stack

```bash
./scripts/mac_stack_up.sh
```

Check the local health endpoint:

```bash
curl -s http://127.0.0.1:8420/healthz
```

Expected response:

```text
ok
```

## 4. Install auto-start on the Mac

```bash
./scripts/install_mac_launch_agent.sh
```

This does three things:

- generates a user-level `launchd` plist
- starts the stack once on login
- resumes the existing Docker stack without rebuilding it
- waits for Docker Desktop or OrbStack to become ready before giving up

Useful commands:

```bash
./scripts/uninstall_mac_launch_agent.sh
./scripts/mac_stack_logs.sh
./scripts/mac_stack_down.sh
./scripts/mac_stack_resume.sh
./scripts/mac_enable_tailscale_serve.sh
```

## 5. Expose it through Tailscale only

Once the app works locally, publish it inside the tailnet:

```bash
./scripts/mac_enable_tailscale_serve.sh
```

Then check:

- `tailscale status`
- `tailscale serve status`

Open the served URL from another device that is already inside the same tailnet.

## 6. First operator smoke test

1. open the dashboard through Tailscale
2. sign in with the Basic Auth credentials
3. open the latest batch
4. build review artifacts if needed
5. approve one `threads` item
6. queue approved
7. confirm `social/approval`, `social/outbox`, and `social/status` changed remotely

## Notes

- the default bind host is `127.0.0.1`
- if you set `MNL_SOCIAL_BIND_HOST=0.0.0.0`, devices on the same local network can open `http://<mac-ip>:8420`
- Tailscale is still the cleaner long-term access path when you want access outside the local network
- `restart: unless-stopped` keeps the container running after Docker restarts
- `launchd` here is a user `LaunchAgent`, so it runs after user login, not before login at pure boot time
- `./scripts/mac_stack_up.sh` is still the manual command for rebuilds after code changes
