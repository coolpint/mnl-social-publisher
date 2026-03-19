from __future__ import annotations

from html import escape
import json
from pathlib import Path
from urllib.parse import parse_qs, urlencode
from wsgiref.simple_server import make_server

from .approval_loader import approval_for_package, save_approval_decision
from .package_loader import load_batch, load_package
from .platforms import supported_platforms
from .publishers.requests import create_publish_requests
from .review_artifacts import artifact_filenames
from .review_builds import build_review_all_batch
from .settings import Settings
from .social_status import build_article_status_path, build_batch_status_path, local_status_path


APP_CSS = """
:root {
  --bg: #f4efe4;
  --panel: rgba(255, 251, 245, 0.92);
  --ink: #1f1b16;
  --muted: #6f6255;
  --accent: #bb4d00;
  --accent-2: #0f766e;
  --line: rgba(71, 52, 33, 0.12);
  --shadow: 0 24px 70px rgba(52, 34, 15, 0.12);
  --radius: 22px;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Avenir Next", "Segoe UI Variable", "Helvetica Neue", sans-serif;
  color: var(--ink);
  background:
    radial-gradient(circle at top left, rgba(187, 77, 0, 0.18), transparent 28%),
    radial-gradient(circle at top right, rgba(15, 118, 110, 0.14), transparent 24%),
    linear-gradient(180deg, #f8f4ea 0%, #efe4d1 100%);
}
a { color: inherit; }
.shell { max-width: 1320px; margin: 0 auto; padding: 28px 20px 56px; }
.hero {
  background: linear-gradient(135deg, rgba(28, 23, 19, 0.96), rgba(76, 43, 18, 0.9));
  color: #f9f5ee;
  border-radius: 30px;
  padding: 28px 30px;
  box-shadow: var(--shadow);
  position: relative;
  overflow: hidden;
}
.hero:after {
  content: "";
  position: absolute;
  inset: auto -40px -40px auto;
  width: 220px;
  height: 220px;
  background: radial-gradient(circle, rgba(255,255,255,0.18), transparent 62%);
}
.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 12px;
  opacity: 0.7;
}
h1, h2, h3 {
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
  margin: 0;
}
h1 { font-size: 40px; line-height: 1.02; margin-top: 10px; }
h2 { font-size: 30px; margin-bottom: 10px; }
h3 { font-size: 20px; margin-bottom: 10px; }
.hero p { max-width: 760px; color: rgba(249, 245, 238, 0.82); }
.nav {
  display: flex;
  gap: 12px;
  margin-top: 18px;
  flex-wrap: wrap;
}
.nav a, .button, button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: rgba(255,255,255,0.1);
  color: inherit;
  text-decoration: none;
  cursor: pointer;
  font: inherit;
}
.button.primary, button.primary {
  background: var(--accent);
  color: #fff8f2;
}
.button.secondary, button.secondary {
  background: rgba(15, 118, 110, 0.12);
  color: #e9fbf8;
  border-color: rgba(255,255,255,0.18);
}
.button.ghost, button.ghost {
  background: transparent;
  border-color: rgba(255,255,255,0.2);
}
.grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 18px;
  margin-top: 22px;
}
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 22px;
  box-shadow: 0 10px 30px rgba(44, 26, 10, 0.05);
}
.span-12 { grid-column: span 12; }
.span-8 { grid-column: span 8; }
.span-6 { grid-column: span 6; }
.span-4 { grid-column: span 4; }
.meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  color: var(--muted);
  font-size: 14px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  background: rgba(31, 27, 22, 0.06);
}
.chip.good { background: rgba(15, 118, 110, 0.12); color: #0d5b55; }
.chip.warn { background: rgba(187, 77, 0, 0.12); color: #8b3d05; }
.chip.blocked { background: rgba(154, 52, 18, 0.12); color: #8f2d17; }
table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 14px;
}
th, td {
  padding: 12px 10px;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
  text-align: left;
}
th { color: var(--muted); font-size: 13px; font-weight: 600; }
tr:last-child td { border-bottom: none; }
.stack { display: grid; gap: 12px; }
.platform-card {
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 18px;
  background: rgba(255,255,255,0.52);
}
pre {
  white-space: pre-wrap;
  word-break: break-word;
  background: rgba(31, 27, 22, 0.04);
  border-radius: 16px;
  padding: 14px;
  font-family: "SF Mono", "Monaco", monospace;
  font-size: 13px;
  line-height: 1.55;
  margin: 0;
}
textarea, input[type="text"] {
  width: 100%;
  border-radius: 14px;
  border: 1px solid var(--line);
  padding: 12px 14px;
  font: inherit;
  background: rgba(255,255,255,0.75);
}
textarea { min-height: 88px; resize: vertical; }
form.inline { display: inline-flex; gap: 10px; flex-wrap: wrap; }
form.stack { display: grid; gap: 10px; }
.flash {
  margin-top: 18px;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(15, 118, 110, 0.1);
  border: 1px solid rgba(15, 118, 110, 0.16);
  color: #0b5b54;
}
.empty {
  color: var(--muted);
  border: 1px dashed var(--line);
  border-radius: 18px;
  padding: 20px;
}
@media (max-width: 980px) {
  .span-8, .span-6, .span-4 { grid-column: span 12; }
  h1 { font-size: 32px; }
}
"""


def serve_web_app(settings: Settings, host: str = "127.0.0.1", port: int = 8420) -> None:
    app = create_web_app(settings)
    with make_server(host, port, app) as server:
        print(f"Serving Money & Law Social Desk on http://{host}:{port}")
        server.serve_forever()


def create_web_app(settings: Settings):
    return SocialDeskApp(settings)


class SocialDeskApp:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")

        try:
            if method == "GET" and path == "/":
                return self._html_response(start_response, self._dashboard_page(environ))
            if method == "GET" and path == "/batch":
                return self._html_response(start_response, self._batch_page(environ))
            if method == "GET" and path == "/article":
                return self._html_response(start_response, self._article_page(environ))
            if method == "POST" and path == "/actions/build-review-all":
                return self._handle_build_review_all(environ, start_response)
            if method == "POST" and path == "/actions/approve":
                return self._handle_approve(environ, start_response)
            if method == "POST" and path == "/actions/create-publish-requests":
                return self._handle_create_publish_requests(environ, start_response)
        except Exception as exc:
            return self._html_response(
                start_response,
                self._layout(
                    "Error",
                    f"<div class='panel span-12'><h2>Something broke</h2><p>{escape(str(exc))}</p></div>",
                    current="error",
                ),
                status="500 Internal Server Error",
            )

        return self._html_response(
            start_response,
            self._layout(
                "Not Found",
                "<div class='panel span-12'><h2>Page not found</h2></div>",
                current="missing",
            ),
            status="404 Not Found",
        )

    def _query(self, environ) -> dict[str, str]:
        parsed = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
        return {key: values[-1] for key, values in parsed.items()}

    def _post(self, environ) -> dict[str, str]:
        length = int(environ.get("CONTENT_LENGTH") or "0")
        raw = environ["wsgi.input"].read(length) if length else b""
        parsed = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
        return {key: values[-1] for key, values in parsed.items()}

    def _redirect(self, start_response, location: str):
        start_response("303 See Other", [("Location", location)])
        return [b""]

    def _html_response(self, start_response, html: str, status: str = "200 OK"):
        payload = html.encode("utf-8")
        start_response(
            status,
            [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", str(len(payload))),
            ],
        )
        return [payload]

    def _layout(self, title: str, body: str, current: str = "home", flash: str = "") -> str:
        flash_markup = f"<div class='flash'>{escape(flash)}</div>" if flash else ""
        return f"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)} | Money & Law Social Desk</title>
    <style>{APP_CSS}</style>
  </head>
  <body>
    <div class="shell">
      <section class="hero">
        <div class="eyebrow">Money & Law Social Desk</div>
        <h1>Daily Publishing Control Room</h1>
        <p>백업 exporter가 만든 inbox를 읽고, review 산출물 생성부터 승인과 publish request 큐잉까지 브라우저에서 운영하는 MVP입니다.</p>
        <div class="nav">
          <a class="button ghost" href="/">Dashboard</a>
        </div>
      </section>
      {flash_markup}
      <section class="grid">
        {body}
      </section>
    </div>
  </body>
</html>"""

    def _dashboard_page(self, environ) -> str:
        query = self._query(environ)
        flash = query.get("flash", "")
        if self.settings.inbox_root is None:
            body = "<div class='panel span-12'><h2>Missing Inbox Root</h2><p>`MNL_SOCIAL_INBOX_ROOT`를 설정하면 대시보드가 실제 batch를 읽을 수 있습니다.</p></div>"
            return self._layout("Dashboard", body, flash=flash)

        batch_cards = []
        for batch in self._recent_batches(self.settings.inbox_root):
            batch_cards.append(self._batch_card(batch))

        if not batch_cards:
            batch_cards.append("<div class='panel span-12 empty'>아직 읽을 수 있는 batch가 없습니다.</div>")

        config_panel = self._config_panel()
        body = config_panel + "".join(batch_cards)
        return self._layout("Dashboard", body, flash=flash)

    def _batch_page(self, environ) -> str:
        query = self._query(environ)
        relative_dir = query.get("relative_dir", "")
        flash = query.get("flash", "")
        batch = self._load_batch_from_relative_dir(relative_dir)
        cards = [
            self._batch_header_card(batch),
            self._batch_articles_table(batch),
            self._batch_status_panel(batch),
        ]
        return self._layout(f"Batch {relative_dir}", "".join(cards), current="batch", flash=flash)

    def _article_page(self, environ) -> str:
        query = self._query(environ)
        relative_dir = query.get("relative_dir", "")
        package_id = query.get("package_id", "")
        flash = query.get("flash", "")
        batch = self._load_batch_from_relative_dir(relative_dir)
        package = load_package(batch.batch_dir / package_id)

        body = [
            f"""
            <div class="panel span-12">
              <div class="eyebrow">Article Review</div>
              <h2>{escape(package.article.headline)}</h2>
              <div class="meta">
                <span>{escape(relative_dir)}</span>
                <span>idxno {package.article.idxno}</span>
                <span>{escape(package.article.section_name or '미분류')}</span>
              </div>
              <p>{escape(package.article.summary or package.article.body_text[:220])}</p>
              <div class="nav">
                <a class="button ghost" href="/batch?{urlencode({'relative_dir': relative_dir})}">Back To Batch</a>
                <a class="button ghost" href="{escape(package.article.canonical_url)}">Open Source</a>
              </div>
            </div>
            """,
            self._article_overview_card(relative_dir, package_id),
        ]
        for platform in supported_platforms():
            body.append(self._platform_review_card(batch, package_id, platform))
        return self._layout(package.article.headline, "".join(body), current="article", flash=flash)

    def _recent_batches(self, inbox_root: Path) -> list:
        batch_dirs = sorted(
            {path.parent for path in inbox_root.rglob("batch.json")},
            key=lambda path: path.as_posix(),
            reverse=True,
        )
        batches = []
        for batch_dir in batch_dirs[:24]:
            try:
                batches.append(load_batch(batch_dir))
            except Exception:
                continue
        return batches

    def _config_panel(self) -> str:
        rows = []
        for label, value in (
            ("Inbox", self.settings.inbox_root),
            ("Review", self.settings.review_root),
            ("Approval", self.settings.approval_root),
            ("Outbox", self.settings.outbox_root),
            ("Status", self.settings.status_root),
        ):
            rows.append(f"<span class='chip'>{escape(label)}: {escape(str(value) if value else 'not set')}</span>")
        return f"""
        <div class="panel span-12">
          <div class="eyebrow">Active Roots</div>
          <h2>Workspace Wiring</h2>
          <div class="meta">{''.join(rows)}</div>
        </div>
        """

    def _batch_card(self, batch) -> str:
        params = urlencode({"relative_dir": batch.relative_dir})
        action_forms = [
            f'<a class="button primary" href="/batch?{params}">Open Batch</a>'
        ]
        if self.settings.review_root is not None:
            action_forms.append(
                f"""
                <form class="inline" method="post" action="/actions/build-review-all">
                  <input type="hidden" name="relative_dir" value="{escape(batch.relative_dir)}">
                  <button type="submit">Build All Review Artifacts</button>
                </form>
                """
            )
        return f"""
        <div class="panel span-6">
          <div class="eyebrow">Batch</div>
          <h2>{escape(batch.relative_dir)}</h2>
          <div class="meta">
            <span>run {batch.run.id}</span>
            <span>{batch.article_count} article(s)</span>
            <span>{escape(batch.exported_at)}</span>
          </div>
          <p>review 결과물을 만들고, 승인된 콘텐츠만 outbox로 넘기는 운영 시작점입니다.</p>
          <div class="nav">
            {''.join(action_forms)}
          </div>
        </div>
        """

    def _batch_header_card(self, batch) -> str:
        action_forms = []
        if self.settings.review_root is not None:
            action_forms.append(
                f"""
                <form class="inline" method="post" action="/actions/build-review-all">
                  <input type="hidden" name="relative_dir" value="{escape(batch.relative_dir)}">
                  <button class="primary" type="submit">Build All Review Artifacts</button>
                </form>
                """
            )
        for platform in supported_platforms():
            if self.settings.review_root is None or self.settings.outbox_root is None:
                continue
            action_forms.append(
                f"""
                <form class="inline" method="post" action="/actions/create-publish-requests">
                  <input type="hidden" name="relative_dir" value="{escape(batch.relative_dir)}">
                  <input type="hidden" name="platform" value="{escape(platform)}">
                  <button type="submit">{escape(platform)} Queue Approved</button>
                </form>
                """
            )

        return f"""
        <div class="panel span-12">
          <div class="eyebrow">Batch Detail</div>
          <h2>{escape(batch.relative_dir)}</h2>
          <div class="meta">
            <span>run {batch.run.id}</span>
            <span>mode {escape(batch.run.mode or 'daily')}</span>
            <span>{batch.article_count} article(s)</span>
          </div>
          <div class="nav">
            <a class="button ghost" href="/">Back</a>
            {''.join(action_forms)}
          </div>
        </div>
        """

    def _batch_articles_table(self, batch) -> str:
        rows = []
        for package_ref in batch.packages:
            package = load_package(batch.batch_dir / package_ref.package_dir)
            params = urlencode({"relative_dir": batch.relative_dir, "package_id": package.package_id})
            status_chips = "".join(
                self._status_chip_for_batch_article(batch, package, platform)
                for platform in supported_platforms()
            )
            rows.append(
                f"""
                <tr>
                  <td><a href="/article?{params}">{escape(package.article.headline)}</a></td>
                  <td>{escape(package.article.section_name or '-')}</td>
                  <td>{status_chips}</td>
                </tr>
                """
            )
        return f"""
        <div class="panel span-8">
          <div class="eyebrow">Articles</div>
          <h2>Review Queue</h2>
          <table>
            <thead>
              <tr>
                <th>Article</th>
                <th>Section</th>
                <th>Platforms</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
        </div>
        """

    def _batch_status_panel(self, batch) -> str:
        items = []
        for platform in supported_platforms():
            status_payload = self._read_batch_status(batch, platform)
            if status_payload is None:
                items.append(f"<div class='chip warn'>{escape(platform)}: no status yet</div>")
            else:
                items.append(
                    f"<div class='chip {'good' if status_payload['state'] in {'approved', 'published'} else 'warn'}'>{escape(platform)}: {escape(status_payload['state'])}</div>"
                )
        return f"""
        <div class="panel span-4">
          <div class="eyebrow">Status</div>
          <h2>Platform Health</h2>
          <div class="stack">{''.join(items)}</div>
        </div>
        """

    def _article_overview_card(self, relative_dir: str, package_id: str) -> str:
        return f"""
        <div class="panel span-12">
          <div class="eyebrow">Operator Note</div>
          <h2>Review Then Dispatch</h2>
          <p>이 화면에서는 플랫폼별 산출물을 확인하고 승인/반려를 남깁니다. 승인된 플랫폼만 outbox request로 넘어갑니다.</p>
          <div class="meta">
            <span>relative_dir: {escape(relative_dir)}</span>
            <span>package: {escape(package_id)}</span>
          </div>
        </div>
        """

    def _platform_review_card(self, batch, package_id: str, platform: str) -> str:
        package = load_package(batch.batch_dir / package_id)
        artifact_dir = None if self.settings.review_root is None else self.settings.review_root / batch.relative_dir / package_id
        approval = approval_for_package(package, batch.relative_dir, self.settings.approval_root)
        decision = None if approval is None else approval.platforms.get(platform)
        status_payload = self._read_article_status(batch, package, platform)

        draft_preview_blocks = []
        if artifact_dir is not None:
            for artifact_name in artifact_filenames(platform):
                path = artifact_dir / artifact_name
                if path.exists():
                    draft_preview_blocks.append(
                        f"<div class='stack'><div class='chip'>{escape(artifact_name)}</div><pre>{escape(path.read_text(encoding='utf-8'))}</pre></div>"
                    )

        if not draft_preview_blocks:
            draft_preview_blocks.append("<div class='empty'>아직 review artifact가 없습니다.</div>")

        approval_markup = "<div class='chip warn'>no approval yet</div>"
        if decision is not None:
            approval_markup = (
                f"<div class='chip {'good' if decision.approved else 'blocked'}'>{escape('approved' if decision.approved else 'rejected')} by {escape(decision.decided_by or 'unknown')}</div>"
            )
        status_markup = ""
        if status_payload is not None:
            status_markup = f"<div class='chip'>{escape(status_payload.get('state', 'unknown'))}</div>"

        form_markup = ""
        if self.settings.approval_root is not None:
            form_markup = f"""
            <form class="stack" method="post" action="/actions/approve">
              <input type="hidden" name="relative_dir" value="{escape(batch.relative_dir)}">
              <input type="hidden" name="package_id" value="{escape(package.package_id)}">
              <input type="hidden" name="article_idxno" value="{package.article.idxno}">
              <input type="hidden" name="platform" value="{escape(platform)}">
              <input type="text" name="decided_by" placeholder="reviewer name or email">
              <textarea name="note" placeholder="review note"></textarea>
              <div class="nav">
                <button class="primary" type="submit" name="decision" value="approve">Approve</button>
                <button type="submit" name="decision" value="reject">Reject</button>
              </div>
            </form>
            """

        return f"""
        <div class="panel span-6">
          <div class="eyebrow">{escape(platform)}</div>
          <h3>{escape(package.article.headline)}</h3>
          <div class="meta">
            {approval_markup}
            {status_markup}
          </div>
          <div class="stack">
            {''.join(draft_preview_blocks)}
            {form_markup}
          </div>
        </div>
        """

    def _status_chip_for_batch_article(self, batch, package, platform: str) -> str:
        status_payload = self._read_article_status(batch, package, platform)
        if status_payload is None:
            return f"<span class='chip'>{escape(platform)}: idle</span>"
        state = str(status_payload.get("state") or "unknown")
        cls = "chip"
        if state in {"approved", "published"}:
            cls += " good"
        elif state in {"blocked", "failed"}:
            cls += " blocked"
        else:
            cls += " warn"
        return f"<span class='{cls}'>{escape(platform)}: {escape(state)}</span>"

    def _read_batch_status(self, batch, platform: str) -> dict | None:
        if self.settings.status_root is None:
            return None
        contract_path = str(
            batch.status_contract.get("batch_path_template")
            or build_batch_status_path(platform, batch.relative_dir)
        ).format(platform=platform)
        local_path = local_status_path(self.settings.status_root, contract_path)
        if not local_path.exists():
            return None
        return json.loads(local_path.read_text(encoding="utf-8"))

    def _read_article_status(self, batch, package, platform: str) -> dict | None:
        if self.settings.status_root is None:
            return None
        target = package.platforms.get(platform)
        contract_path = "" if target is None else target.status_article_path
        if not contract_path:
            template = str(
                batch.status_contract.get("article_path_template")
                or build_article_status_path(platform, batch.relative_dir, package.article.idxno)
            )
            contract_path = template.format(platform=platform, idxno=package.article.idxno)
        local_path = local_status_path(self.settings.status_root, contract_path)
        if not local_path.exists():
            return None
        return json.loads(local_path.read_text(encoding="utf-8"))

    def _load_batch_from_relative_dir(self, relative_dir: str):
        if self.settings.inbox_root is None:
            raise ValueError("Inbox root is not configured")
        return load_batch(self.settings.inbox_root / relative_dir)

    def _handle_build_review_all(self, environ, start_response):
        form = self._post(environ)
        relative_dir = form.get("relative_dir", "")
        if self.settings.review_root is None:
            return self._redirect(start_response, f"/batch?{urlencode({'relative_dir': relative_dir, 'flash': 'Review root is not configured.'})}")
        batch = self._load_batch_from_relative_dir(relative_dir)
        summary = build_review_all_batch(batch, output_root=self.settings.review_root, pretty=True)
        message = f"Built review artifacts for {summary['platform_count']} platforms."
        return self._redirect(start_response, f"/batch?{urlencode({'relative_dir': relative_dir, 'flash': message})}")

    def _handle_approve(self, environ, start_response):
        form = self._post(environ)
        relative_dir = form.get("relative_dir", "")
        package_id = form.get("package_id", "")
        article_idxno = int(form.get("article_idxno", "0"))
        platform = form.get("platform", "")
        decision = form.get("decision", "")
        decided_by = form.get("decided_by", "").strip() or "operator"
        note = form.get("note", "").strip()
        if self.settings.approval_root is None:
            return self._redirect(start_response, f"/article?{urlencode({'relative_dir': relative_dir, 'package_id': package_id, 'flash': 'Approval root is not configured.'})}")
        save_approval_decision(
            approval_root=self.settings.approval_root,
            relative_dir=relative_dir,
            package_id=package_id,
            article_idxno=article_idxno,
            platform=platform,
            approved=(decision == "approve"),
            decided_by=decided_by,
            note=note,
        )
        message = f"{platform} {'approved' if decision == 'approve' else 'rejected'}."
        return self._redirect(start_response, f"/article?{urlencode({'relative_dir': relative_dir, 'package_id': package_id, 'flash': message})}")

    def _handle_create_publish_requests(self, environ, start_response):
        form = self._post(environ)
        relative_dir = form.get("relative_dir", "")
        platform = form.get("platform", "")
        if self.settings.review_root is None or self.settings.outbox_root is None:
            return self._redirect(start_response, f"/batch?{urlencode({'relative_dir': relative_dir, 'flash': 'Review root or outbox root is not configured.'})}")
        batch = self._load_batch_from_relative_dir(relative_dir)
        summary = create_publish_requests(
            platform,
            batch,
            review_root=self.settings.review_root,
            approval_root=self.settings.approval_root,
            outbox_root=self.settings.outbox_root,
            status_root=self.settings.status_root,
            pretty=True,
        )
        message = f"{platform}: queued {summary['request_count']} publish request(s)."
        return self._redirect(start_response, f"/batch?{urlencode({'relative_dir': relative_dir, 'flash': message})}")
