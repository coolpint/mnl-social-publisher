# mnl-social-publisher

`mnl-social-publisher` consumes social export batches from the Money & Law backup system and turns them into platform-specific drafts and publishing jobs.

This repository does not scrape articles or manage archival storage. Its job starts after `mnl-backup` has already exported a canonical social package.

## Responsibilities

- Validate incoming social packages.
- Build platform-specific content drafts from shared article facts.
- Publish approved drafts to each platform through isolated adapters.
- Record per-platform status without coupling platform failures to the backup pipeline.

## Non-responsibilities

- Article scraping
- Backup orchestration
- SharePoint sync logic
- Canonical archive generation

## Initial scope

The first milestone in this repository is a YouTube Shorts MVP:

1. Load a batch or notification exported by `mnl-backup`
2. Validate package, batch, and notification metadata
3. Build reviewable YouTube drafts for every package in the batch
4. Keep publisher logic separate from the draft builder

Other channels now start from the same contract as separate builders and publishers:

- `youtube_shorts`
- `threads`
- `x`
- `facebook`
- `instagram`

Builder copy is now externalized into prompt template files under `src/mnl_social_publisher/prompts`, and platform strategy now lives in generation profiles under `src/mnl_social_publisher/profiles/platforms`, so tone, length, scene shape, and hashtag behavior can be tuned without reopening builder code.
Approval input is now split into separate modules as well:

- `src/mnl_social_publisher/approval_inputs.py`
  current browser form handler and future approval channel adapters
- `src/mnl_social_publisher/approval_stores.py`
  approval persistence backends for local JSON and remote OneDrive JSON

## Package contract

The expected input contract lives in [docs/package-contract.md](docs/package-contract.md).

At a high level, the publisher consumes a folder like this:

```text
social/inbox/YYYY/MM/DD/run-000123/
  batch.json
  notification.json
  article-000143/
    package.json
    article.json
    rights.json
    article.xml
    source.html
    body.txt
    assets/
      source-media/
```

## Local development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
python3 -m unittest discover -s tests
```

Validate a fixture package:

```bash
mnl-social-publisher validate-package \
  tests/fixtures/social_inbox/2026/03/14/run-000123/article-000143
```

Validate a fixture batch:

```bash
mnl-social-publisher validate-batch \
  tests/fixtures/social_inbox/2026/03/14/run-000123
```

Build YouTube drafts directly from a batch:

```bash
mnl-social-publisher build-youtube-batch \
  tests/fixtures/social_inbox/2026/03/14/run-000123 \
  --pretty
```

Build review drafts for a text platform:

```bash
mnl-social-publisher build-review-batch \
  threads \
  tests/fixtures/social_inbox/2026/03/14/run-000123 \
  --pretty
```

Build every platform review artifact in one run:

```bash
mnl-social-publisher build-review-all-notification \
  tests/fixtures/social_notifications/latest.json \
  --inbox-root tests/fixtures/social_inbox \
  --output-root /path/to/social/review \
  --pretty
```

Build YouTube drafts from a notification:

```bash
mnl-social-publisher build-youtube-notification \
  tests/fixtures/social_notifications/latest.json \
  --inbox-root tests/fixtures/social_inbox \
  --pretty
```

Prepare platform-specific publisher jobs after drafts are built:

```bash
mnl-social-publisher prepare-publish-batch \
  x \
  tests/fixtures/social_inbox/2026/03/14/run-000123 \
  --review-root /path/to/social/review \
  --approval-root /path/to/social/approval \
  --status-root /path/to/social/status \
  --pretty
```

Create publish requests for approved items:

```bash
mnl-social-publisher create-publish-requests-batch \
  threads \
  tests/fixtures/social_inbox/2026/03/14/run-000123 \
  --review-root /path/to/social/review \
  --approval-root /path/to/social/approval \
  --outbox-root /path/to/social/outbox \
  --status-root /path/to/social/status \
  --pretty
```

Run the browser UI locally:

```bash
MNL_SOCIAL_INBOX_ROOT=/path/to/social/inbox \
MNL_SOCIAL_REVIEW_ROOT=/path/to/social/review \
MNL_SOCIAL_APPROVAL_ROOT=/path/to/social/approval \
MNL_SOCIAL_OUTBOX_ROOT=/path/to/social/outbox \
MNL_SOCIAL_STATUS_ROOT=/path/to/social/status \
PYTHONPATH=src python3 -m mnl_social_publisher serve-web --host 127.0.0.1 --port 8420
```

Run the browser UI without any local SharePoint sync:

```bash
MNL_SOCIAL_STORAGE_BACKEND=onedrive \
MNL_SOCIAL_INBOX_REMOTE_ROOT=social/inbox \
MNL_SOCIAL_REVIEW_REMOTE_ROOT=social/review \
MNL_SOCIAL_APPROVAL_REMOTE_ROOT=social/approval \
MNL_SOCIAL_OUTBOX_REMOTE_ROOT=social/outbox \
MNL_SOCIAL_STATUS_REMOTE_ROOT=social/status \
MNL_ONEDRIVE_TENANT_ID=... \
MNL_ONEDRIVE_CLIENT_ID=... \
MNL_ONEDRIVE_CLIENT_SECRET=... \
MNL_ONEDRIVE_DRIVE_ID=... \
PYTHONPATH=src python3 -m mnl_social_publisher serve-web --host 0.0.0.0 --port 8420
```

In `onedrive` mode the app reads `social/inbox`, writes `social/review`, `social/approval`, `social/outbox`, and `social/status` back to Microsoft Graph directly. A local SharePoint/OneDrive sync folder is not required. The current implementation stages files only in a temporary runtime workspace while each request is being processed; the system of record remains the remote drive.

Those remote roots are Graph app-folder relative paths. In SharePoint they typically appear under a visible path like `Apps/mnl-backup-prod/social/inbox`, `Apps/mnl-backup-prod/social/review`, and so on.

## Prompt and storyboard outputs

- Text builders use prompt templates in `src/mnl_social_publisher/prompts/builders/`.
- Platform strategy profiles live in `src/mnl_social_publisher/profiles/platforms/`.
- `youtube_shorts` now produces both a draft JSON and scene-level review artifacts:
  - `youtube_storyboard.txt`
  - `youtube_scenes.json`
- The YouTube publish payload now includes scene timing and thumbnail text so a renderer or uploader can consume the same review draft directly.
- Review artifacts and publish requests also carry the profile and prompt metadata that produced the draft.

### Tuning surfaces

- Prompt templates:
  editing wording and copy structure in `src/mnl_social_publisher/prompts/`
- Generation profiles:
  editing platform-specific strategy such as story point limits, title suffixes, scene timing, character caps, and fallback visual modes in `src/mnl_social_publisher/profiles/platforms/`
- Approval input:
  editing how decisions enter the system in `src/mnl_social_publisher/approval_inputs.py`
- Approval storage:
  editing where decisions are saved in `src/mnl_social_publisher/approval_stores.py`

Optional override roots for local experiments:

- `MNL_SOCIAL_TEMPLATE_ROOT`
- `MNL_SOCIAL_PROFILE_ROOT`

## GitHub Actions

This repository now ships with two workflows:

- `.github/workflows/mnl-social-publisher-ci.yml`
  Runs the unit test suite on every push to `main` and on pull requests.
- `.github/workflows/mnl-social-publisher-remote-ops.yml`
  Lets an operator manually run remote OneDrive-backed jobs from the Actions tab.
- `.github/workflows/mnl-social-publisher-web-image.yml`
  Builds and publishes a container image to GHCR on every push to `main`.

The remote ops workflow uses the same Microsoft Graph secrets as `mnl-backup`:

- `MNL_ONEDRIVE_TENANT_ID`
- `MNL_ONEDRIVE_CLIENT_ID`
- `MNL_ONEDRIVE_CLIENT_SECRET`
- `MNL_ONEDRIVE_DRIVE_ID`

Supported manual operations:

- `list_batches`
- `build_review_all`
- `queue_publish_requests`

Optional notifier secrets for `remote-ops`:

- `MNL_SOCIAL_NOTIFY_TEAMS_WEBHOOK_URL`
- `MNL_SOCIAL_NOTIFY_SLACK_WEBHOOK_URL`

When `notify=true`, the workflow sends a short operation summary after `build_review_all` or `queue_publish_requests`. Notification delivery is best-effort and does not fail the main job.

## Next Tuning Surface

- Content generation quality can now be tuned at two layers:
  prompt templates under `src/mnl_social_publisher/prompts/` and platform strategy profiles under `src/mnl_social_publisher/profiles/platforms/`.
- Approval collection can be tuned independently at the input/store layer without changing publisher logic.

The remote ops workflow targets these remote roots by default:

- `social/inbox`
- `social/review`
- `social/approval`
- `social/outbox`
- `social/status`

## Remote web deployment

The web UI is now packaged for remote deployment as a containerized WSGI app.

- Container entrypoint:
  `gunicorn mnl_social_publisher.wsgi:app`
- Health check:
  `GET /healthz`
- Optional protection:
  `MNL_SOCIAL_WEB_BASIC_AUTH_USERNAME`
  `MNL_SOCIAL_WEB_BASIC_AUTH_PASSWORD`

Required runtime environment for the remote app:

- `MNL_SOCIAL_STORAGE_BACKEND=onedrive`
- `MNL_SOCIAL_INBOX_REMOTE_ROOT=social/inbox`
- `MNL_SOCIAL_REVIEW_REMOTE_ROOT=social/review`
- `MNL_SOCIAL_APPROVAL_REMOTE_ROOT=social/approval`
- `MNL_SOCIAL_OUTBOX_REMOTE_ROOT=social/outbox`
- `MNL_SOCIAL_STATUS_REMOTE_ROOT=social/status`
- `MNL_ONEDRIVE_TENANT_ID`
- `MNL_ONEDRIVE_CLIENT_ID`
- `MNL_ONEDRIVE_CLIENT_SECRET`
- `MNL_ONEDRIVE_DRIVE_ID`

The image workflow publishes to `ghcr.io/<owner>/mnl-social-publisher`. A hosting platform only needs to run that image with the environment above.

See [docs/REMOTE_WEB_UI.md](docs/REMOTE_WEB_UI.md) for the rollout checklist.
If the first production host is a Mac on your Tailscale network, use [docs/MAC_DOCKER_DEPLOYMENT.md](docs/MAC_DOCKER_DEPLOYMENT.md).
