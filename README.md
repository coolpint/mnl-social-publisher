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
