# Social Package Contract

This repository consumes the social export contract written by `mnl-backup`.

The contract has three layers:

- `notification.json`: event pointer that tells publishers a new batch is ready
- `batch.json`: manifest for one exporter run
- `article-xxxxxx/`: self-contained article package

Builders can share the same source facts while still producing different outputs for YouTube, Instagram, Facebook, or Threads.

## Directory layout

```text
social/
  inbox/YYYY/MM/DD/run-000123/
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
  notifications/YYYY/MM/DD/run-000123.json
  notifications/latest.json
```

## `notification.json`

Required fields:

- `schema_version`
- `event_kind`
- `exported_at`
- `relative_dir`
- `batch_manifest`
- `article_count`
- `publisher_targets`
- `packages`

`relative_dir` points to the matching inbox batch, for example `2026/03/14/run-000123`.

## `batch.json`

Required fields:

- `schema_version`
- `export_kind`
- `exported_at`
- `relative_dir`
- `run`
- `article_count`
- `packages`

Exporter may also include `status_contract`, which tells publishers exactly where platform status files should be written.

Each package entry includes:

- `article_idxno`
- `headline`
- `change_type`
- `package_dir`
- `package_path`
- `article_json_path`
- `rights_path`
- `asset_count`

## `package.json`

Required fields:

- `schema_version`
- `export_kind`
- `exported_at`
- `run`
- `article`
- `files`
- `assets`
- `platforms`

Important nested fields:

- `files.article_json`
- `files.article_xml`
- `files.source_html`
- `files.body_text`
- `files.rights`
- `platforms.youtube_shorts`
- `platforms.<name>.status_paths.batch`
- `platforms.<name>.status_paths.article`

## `article.json`

Required fields:

- `schema_version`
- `article`
- `assets`

Recommended fields:

- `article.summary`
- `article.body_text`
- `article.section_name`
- `article.subsection_name`
- `article.author_name`
- `article.canonical_url`
- `article.change_type`

`body.txt` mirrors `article.body_text` in plain text so LLM/TTS/subtitle tooling can consume the package without parsing JSON.

## `rights.json`

Required fields:

- `schema_version`
- `status`
- `article_idxno`
- `article_text`
- `music`

Recommended fields:

- `media[]`
- `article_text.notes`
- `article_text.transformation_required`
- `music.license_required`

The exporter is intentionally conservative. Article transformation is required, attached images default to `social_use_allowed=false`, and music always requires a separate license decision.

## Output model

This repository writes generated drafts into a separate review root.

Example review target:

```text
social/review/YYYY/MM/DD/run-000123/
  youtube_build.json
  threads_build.json
  x_build.json
  facebook_build.json
  instagram_build.json
  article-000143/
    youtube_draft.json
    threads_draft.json
    x_draft.json
    facebook_draft.json
    instagram_draft.json
```

Example approval target:

```text
social/approval/YYYY/MM/DD/run-000123/
  article-000143.json
```

Approval file example:

```json
{
  "schema_version": 1,
  "approval_kind": "mnl/social-approval",
  "package_id": "article-000143",
  "article_idxno": 143,
  "platforms": {
    "threads": {
      "approved": true,
      "decided_at": "2026-03-14T10:05:00+09:00",
      "decided_by": "editor@example.com",
      "note": "배포 가능"
    }
  }
}
```

Example outbox target:

```text
social/outbox/threads/YYYY/MM/DD/run-000123/
  publish_requests.json
  article-000143.json
```

Example status target:

```text
social/status/threads/YYYY/MM/DD/run-000123/
  publish_batch.json
  article-000143.json
```

Status files are produced by the publisher layer and are separate from both the immutable inbox package and the review drafts.
