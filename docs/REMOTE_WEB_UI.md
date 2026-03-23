# Remote Web UI Rollout

This document is the shortest path to turning `mnl-social-publisher` into an always-on operator app.

## Goal

Run the browser UI remotely so editors can:

- open the latest batch
- inspect review artifacts
- approve or reject by platform
- queue approved items into `social/outbox`

without local SharePoint sync or a long-running local terminal.

## What is already prepared

- the app reads and writes OneDrive roots directly through Microsoft Graph
- the web UI has a health check at `/healthz`
- the web UI can be protected with HTTP Basic Auth
- the repo publishes a container image through GitHub Actions

## Required environment

```text
PORT=8420
WEB_CONCURRENCY=2

MNL_SOCIAL_STORAGE_BACKEND=onedrive
MNL_SOCIAL_INBOX_REMOTE_ROOT=social/inbox
MNL_SOCIAL_REVIEW_REMOTE_ROOT=social/review
MNL_SOCIAL_APPROVAL_REMOTE_ROOT=social/approval
MNL_SOCIAL_OUTBOX_REMOTE_ROOT=social/outbox
MNL_SOCIAL_STATUS_REMOTE_ROOT=social/status

MNL_ONEDRIVE_TENANT_ID=...
MNL_ONEDRIVE_CLIENT_ID=...
MNL_ONEDRIVE_CLIENT_SECRET=...
MNL_ONEDRIVE_DRIVE_ID=...

MNL_SOCIAL_WEB_BASIC_AUTH_USERNAME=...
MNL_SOCIAL_WEB_BASIC_AUTH_PASSWORD=...
```

## Image source

The workflow `.github/workflows/mnl-social-publisher-web-image.yml` publishes:

- `ghcr.io/<owner>/mnl-social-publisher:latest`
- `ghcr.io/<owner>/mnl-social-publisher:main`
- `ghcr.io/<owner>/mnl-social-publisher:sha-<commit>`

## Recommended rollout order

1. Run the image workflow once and confirm the package appears in GHCR.
2. Deploy the image to a container host.
3. Set all OneDrive and web auth environment variables.
4. Confirm `/healthz` returns `ok`.
5. Open `/` and confirm the latest batch appears.
6. Build review artifacts from the UI.
7. Approve one `threads` article and queue it.
8. Confirm `social/approval`, `social/outbox`, and `social/status` changed remotely.

## First smoke test

Use the current known batch:

- `2026/03/23/run-000013`

Expected operator flow:

1. open dashboard
2. open `run-000013`
3. inspect `threads`, `x`, `facebook`, `instagram`, `youtube_shorts`
4. approve one platform
5. queue approved

## Security notes

- do not expose the app publicly without `MNL_SOCIAL_WEB_BASIC_AUTH_USERNAME` and `MNL_SOCIAL_WEB_BASIC_AUTH_PASSWORD`
- keep Microsoft Graph credentials only in the host's secret manager
- use HTTPS on the hosting platform

## What comes next

Once the remote UI is reachable, the next user-facing improvements should be:

- batch filtering and search
- inline editing of generated drafts before approval
- profile selection or profile preview per platform
- richer approval history and audit trail
