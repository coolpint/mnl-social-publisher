from __future__ import annotations

import base64
from html import escape
from urllib.parse import parse_qs, urlencode
from wsgiref.simple_server import make_server

from .approval_inputs import (
    ApprovalInputError,
    BaseApprovalInputHandler,
    default_approval_input_handler,
)
from .platforms import display_platform_name, supported_platforms
from .review_artifacts import artifact_filenames
from .settings import Settings
from .workspace import BaseWorkspace, WorkspaceError, workspace_from_settings


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
.stat-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 22px;
}
.stat-card {
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 22px;
  padding: 16px 18px;
}
.stat-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  opacity: 0.68;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  margin-top: 8px;
}
.stat-note {
  font-size: 13px;
  margin-top: 6px;
  color: rgba(249, 245, 238, 0.75);
}
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
.action-stack { display: grid; gap: 10px; margin-top: 16px; }
.story-list {
  display: grid;
  gap: 10px;
  margin-top: 16px;
}
.story-item {
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 12px 14px;
  background: rgba(255,255,255,0.54);
}
.story-item strong {
  display: block;
  margin-bottom: 6px;
}
.anchor-nav {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 16px;
}
.anchor-link {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(31, 27, 22, 0.06);
  text-decoration: none;
  font-size: 13px;
}
.article-shell {
  display: grid;
  gap: 18px;
}
.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.helper {
  color: var(--muted);
  font-size: 14px;
  line-height: 1.5;
}
.muted-link {
  color: var(--accent-2);
  text-decoration: none;
}
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
  .stat-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
"""


def serve_web_app(settings: Settings, host: str = "127.0.0.1", port: int = 8420) -> None:
    app = create_web_app(settings)
    with make_server(host, port, app) as server:
        print(f"Serving Money & Law Social Desk on http://{host}:{port}")
        server.serve_forever()


def create_web_app(
    settings: Settings,
    workspace: BaseWorkspace | None = None,
    approval_input: BaseApprovalInputHandler | None = None,
):
    return SocialDeskApp(
        settings,
        workspace or workspace_from_settings(settings),
        approval_input=approval_input or default_approval_input_handler(),
    )


class SocialDeskApp:
    def __init__(
        self,
        settings: Settings,
        workspace: BaseWorkspace,
        approval_input: BaseApprovalInputHandler,
    ) -> None:
        self.settings = settings
        self.workspace = workspace
        self.approval_input = approval_input

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")

        if method == "GET" and path == "/healthz":
            return self._text_response(start_response, "ok\n")

        if not self._is_authorized(environ):
            return self._unauthorized_response(start_response)

        try:
            if method == "GET" and path == "/":
                return self._html_response(start_response, self._dashboard_page(environ))
            if method == "GET" and path == "/batch":
                return self._html_response(start_response, self._batch_page(environ))
            if method == "GET" and path == "/article":
                return self._html_response(start_response, self._article_page(environ))
            if method == "GET" and path == "/actions/build-review-all":
                return self._html_response(start_response, self._build_review_all_confirm_page(environ))
            if method == "GET" and path == "/actions/create-publish-requests":
                return self._html_response(start_response, self._create_publish_requests_confirm_page(environ))
            if method == "GET" and path == "/actions/approve":
                return self._html_response(start_response, self._approval_action_help_page(environ))
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
                    "오류",
                    f"<div class='panel span-12'><h2>문제가 생겼습니다</h2><p>{escape(str(exc))}</p></div>",
                    current="error",
                ),
                status="500 Internal Server Error",
            )

        return self._html_response(
            start_response,
            self._layout(
                "찾을 수 없음",
                "<div class='panel span-12'><h2>페이지를 찾을 수 없습니다</h2></div>",
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

    def _text_response(self, start_response, body: str, status: str = "200 OK"):
        payload = body.encode("utf-8")
        start_response(
            status,
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(len(payload))),
            ],
        )
        return [payload]

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

    def _is_authorized(self, environ) -> bool:
        username = self.settings.web_basic_auth_username or ""
        password = self.settings.web_basic_auth_password or ""
        if not username or not password:
            return True

        header = environ.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Basic "):
            return False

        token = header[6:].strip()
        if not token:
            return False
        try:
            decoded = base64.b64decode(token).decode("utf-8")
        except Exception:
            return False

        submitted_username, separator, submitted_password = decoded.partition(":")
        if not separator:
            return False
        return submitted_username == username and submitted_password == password

    def _unauthorized_response(self, start_response):
        body = "Authentication required\n".encode("utf-8")
        start_response(
            "401 Unauthorized",
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(len(body))),
                ("WWW-Authenticate", 'Basic realm="Money & Law Social Desk"'),
            ],
        )
        return [body]

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
        <h1>오늘의 소셜 발행 관리판</h1>
        <p>백업으로 모아진 기사를 읽고, 소셜미디어별 콘텐츠 초안을 만들고, 검토한 뒤 게시 준비까지 이어가는 운영 화면입니다.</p>
        <div class="nav">
          <a class="button ghost" href="/">대시보드</a>
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
        batches = self.workspace.list_recent_batches()
        batch_cards = []
        for batch in batches:
            batch_cards.append(self._batch_card(batch))

        if not batch_cards:
            batch_cards.append("<div class='panel span-12 empty'>아직 읽을 수 있는 기사 묶음이 없습니다.</div>")

        config_panel = self._config_panel()
        summary_panel = self._dashboard_summary_panel(batches)
        body = summary_panel + config_panel + "".join(batch_cards)
        return self._layout("대시보드", body, flash=flash)

    def _batch_page(self, environ) -> str:
        query = self._query(environ)
        relative_dir = query.get("relative_dir", "")
        flash = query.get("flash", "")
        batch = self.workspace.load_batch(relative_dir)
        cards = [
            self._batch_header_card(batch),
            self._batch_articles_table(batch),
            self._batch_status_panel(batch),
        ]
        return self._layout(f"기사 묶음 {relative_dir}", "".join(cards), current="batch", flash=flash)

    def _article_page(self, environ) -> str:
        query = self._query(environ)
        relative_dir = query.get("relative_dir", "")
        package_id = query.get("package_id", "")
        flash = query.get("flash", "")
        batch = self.workspace.load_batch(relative_dir)
        package = self.workspace.load_package(relative_dir, package_id)

        platform_nav = "".join(
            f'<a class="anchor-link" href="#platform-{escape(platform)}">{escape(display_platform_name(platform))}</a>'
            for platform in supported_platforms()
        )
        body = [
            f"""
            <div class="panel span-12">
              <div class="eyebrow">기사별 콘텐츠 보기</div>
              <h2>{escape(package.article.headline)}</h2>
              <div class="meta">
                <span>{escape(relative_dir)}</span>
                <span>기사 번호 {package.article.idxno}</span>
                <span>{escape(package.article.section_name or '분류 없음')}</span>
              </div>
              <p>{escape(package.article.summary or package.article.body_text[:220])}</p>
              <div class="nav">
                <a class="button ghost" href="/batch?{urlencode({'relative_dir': relative_dir})}">기사 묶음으로 돌아가기</a>
                <a class="button ghost" href="{escape(package.article.canonical_url)}">원문 보기</a>
              </div>
              <div class="anchor-nav">{platform_nav}</div>
            </div>
            """,
            self._article_overview_card(relative_dir, package_id),
        ]
        for platform in supported_platforms():
            body.append(self._platform_review_card(batch, package, platform))
        return self._layout(package.article.headline, "".join(body), current="article", flash=flash)

    def _config_panel(self) -> str:
        rows = []
        for label, value in self.workspace.describe_roots():
            rows.append(
                f"<span class='chip'>{escape(_display_root_label(label))}: {escape(_display_root_value(value))}</span>"
            )
        rows.append(
            f"<span class='chip'>승인 입력 방식: {escape(self.approval_input.label)}</span>"
        )
        rows.append(
            f"<span class='chip'>승인 저장 방식: {escape(_display_approval_store_label(self.workspace.approval_store_kind))}</span>"
        )
        return f"""
        <div class="panel span-12">
          <div class="eyebrow">연결 상태</div>
          <h2>저장 위치와 연결 경로</h2>
          <div class="meta">{''.join(rows)}</div>
        </div>
        """

    def _dashboard_summary_panel(self, batches) -> str:
        latest = batches[0] if batches else None
        article_total = sum(batch.article_count for batch in batches)
        cards = [
            ("기사 묶음", str(len(batches)), "현재 보이는 최근 기사 묶음 수"),
            ("기사 수", str(article_total), "최근 기사 묶음 안의 기사 수 합계"),
            (
                "최신 백업",
                "-" if latest is None else str(latest.run.id),
                "가장 최근 백업 실행 번호",
            ),
            (
                "최신 묶음",
                "-" if latest is None else latest.relative_dir.split("/")[-1],
                "바로 열어볼 기사 묶음 이름",
            ),
        ]
        markup = "".join(
            f"""
            <div class="stat-card">
              <div class="stat-label">{escape(label)}</div>
              <div class="stat-value">{escape(value)}</div>
              <div class="stat-note">{escape(note)}</div>
            </div>
            """
            for label, value, note in cards
        )
        return f"""
        <div class="panel span-12">
          <div class="eyebrow">오늘 할 일 요약</div>
          <h2>오늘의 작업 요약</h2>
          <p class="helper">먼저 최신 기사 묶음을 열고 소셜미디어별 콘텐츠 초안을 만든 다음, 기사별 검토와 게시 준비로 넘어가면 됩니다.</p>
          <div class="stat-strip">{markup}</div>
        </div>
        """

    def _build_review_all_confirm_page(self, environ) -> str:
        query = self._query(environ)
        relative_dir = query.get("relative_dir", "")
        if not relative_dir:
            body = """
            <div class="panel span-12">
              <div class="eyebrow">도움말</div>
              <h2>콘텐츠 초안 만들기</h2>
              <p>이 주소는 기사 묶음 안의 기사들을 소셜미디어별 콘텐츠 초안으로 바꾸는 작업용 경로입니다. 대시보드에서 기사 묶음을 연 뒤 버튼을 누르는 방식이 더 자연스럽습니다.</p>
              <div class="nav">
                <a class="button primary" href="/">대시보드로 가기</a>
              </div>
            </div>
            """
            return self._layout("콘텐츠 초안 만들기", body, current="action")

        body = f"""
        <div class="panel span-12">
          <div class="eyebrow">실행 확인</div>
          <h2>콘텐츠 초안 만들기</h2>
          <p><strong>{escape(relative_dir)}</strong> 기사 묶음의 기사들을 소셜미디어별 콘텐츠 초안으로 다시 만듭니다.</p>
          <div class="nav">
            <a class="button ghost" href="/batch?{urlencode({'relative_dir': relative_dir})}">기사 묶음으로 돌아가기</a>
          </div>
        </div>
        <div class="panel span-12">
          <form class="stack" method="post" action="/actions/build-review-all">
            <input type="hidden" name="relative_dir" value="{escape(relative_dir)}">
            <button class="primary" type="submit">소셜미디어별 콘텐츠 초안 만들기</button>
          </form>
        </div>
        """
        return self._layout("콘텐츠 초안 만들기", body, current="action")

    def _create_publish_requests_confirm_page(self, environ) -> str:
        query = self._query(environ)
        relative_dir = query.get("relative_dir", "")
        platform = query.get("platform", "")
        if not relative_dir or not platform:
            body = """
            <div class="panel span-12">
              <div class="eyebrow">도움말</div>
              <h2>게시 준비</h2>
              <p>이 주소는 승인된 콘텐츠를 소셜미디어별 게시 대기 상태로 넘기는 작업용 경로입니다. 기사 묶음 화면에서 버튼을 눌러 실행하는 방식이 맞습니다.</p>
              <div class="nav">
                <a class="button primary" href="/">대시보드로 가기</a>
              </div>
            </div>
            """
            return self._layout("게시 준비", body, current="action")

        body = f"""
        <div class="panel span-12">
          <div class="eyebrow">실행 확인</div>
          <h2>{escape(display_platform_name(platform))} 게시 준비</h2>
          <p><strong>{escape(relative_dir)}</strong> 기사 묶음에서 승인된 <strong>{escape(display_platform_name(platform))}</strong> 콘텐츠만 게시 대기 상태로 넘깁니다.</p>
          <div class="nav">
            <a class="button ghost" href="/batch?{urlencode({'relative_dir': relative_dir})}">기사 묶음으로 돌아가기</a>
          </div>
        </div>
        <div class="panel span-12">
          <form class="stack" method="post" action="/actions/create-publish-requests">
            <input type="hidden" name="relative_dir" value="{escape(relative_dir)}">
            <input type="hidden" name="platform" value="{escape(platform)}">
            <button class="primary" type="submit">{escape(display_platform_name(platform))} 게시 준비하기</button>
          </form>
        </div>
        """
        return self._layout("게시 준비", body, current="action")

    def _approval_action_help_page(self, environ) -> str:
        query = self._query(environ)
        relative_dir = query.get("relative_dir", "")
        package_id = query.get("package_id", "")
        params = {}
        if relative_dir:
            params["relative_dir"] = relative_dir
        if package_id:
            params["package_id"] = package_id
        target = f"/article?{urlencode(params)}" if params else "/"
        body = f"""
        <div class="panel span-12">
          <div class="eyebrow">도움말</div>
          <h2>승인은 기사 화면에서 합니다</h2>
          <p>승인은 직접 URL을 여는 방식이 아니라 기사 상세 화면의 승인 폼에서 처리합니다.</p>
          <div class="nav">
            <a class="button primary" href="{escape(target)}">기사 화면으로 가기</a>
          </div>
        </div>
        """
        return self._layout("승인 안내", body, current="action")

    def _batch_card(self, batch) -> str:
        params = urlencode({"relative_dir": batch.relative_dir})
        action_forms = [
            f'<a class="button primary" href="/batch?{params}">기사 묶음 열기</a>'
        ]
        if self.workspace.has_review_root:
            action_forms.append(
                f'<a class="button secondary" href="/actions/build-review-all?{params}">콘텐츠 초안 만들기</a>'
            )
        story_items = "".join(
            f"""
            <div class="story-item">
              <strong>{escape(package_ref.headline or package_ref.package_dir)}</strong>
              <div class="meta">
                <span>기사 번호 {package_ref.article_idxno}</span>
                <span>{escape(_display_change_type_label(package_ref.change_type))}</span>
              </div>
            </div>
            """
            for package_ref in batch.packages[:3]
        )
        return f"""
        <div class="panel span-6">
          <div class="eyebrow">기사 묶음</div>
          <h2>{escape(batch.relative_dir)}</h2>
          <div class="meta">
            <span>백업 실행 {batch.run.id}</span>
            <span>기사 {batch.article_count}건</span>
            <span>{escape(batch.exported_at)}</span>
          </div>
          <p class="helper">이 기사 묶음에서 소셜미디어별 콘텐츠 초안을 만들고, 검토한 뒤 필요한 것만 게시 준비로 넘깁니다.</p>
          <div class="story-list">{story_items or "<div class='empty'>기사 미리보기가 없습니다.</div>"}</div>
          <div class="action-stack">
            {''.join(action_forms)}
          </div>
        </div>
        """

    def _batch_header_card(self, batch) -> str:
        action_forms = []
        if self.workspace.has_review_root:
            action_forms.append(
                f'<a class="button primary" href="/actions/build-review-all?{urlencode({"relative_dir": batch.relative_dir})}">소셜미디어별 콘텐츠 초안 만들기</a>'
            )
        for platform in supported_platforms():
            if not self.workspace.has_review_root or not self.workspace.has_outbox_root:
                continue
            action_forms.append(
                f'<a class="button ghost" href="/actions/create-publish-requests?{urlencode({"relative_dir": batch.relative_dir, "platform": platform})}">{escape(display_platform_name(platform))} 게시 준비</a>'
            )

        return f"""
        <div class="panel span-12">
          <div class="eyebrow">기사 묶음 상세</div>
          <h2>{escape(batch.relative_dir)}</h2>
          <div class="meta">
            <span>백업 실행 {batch.run.id}</span>
            <span>실행 방식 {escape(_display_batch_mode_label(batch.run.mode))}</span>
            <span>기사 {batch.article_count}건</span>
          </div>
          <p class="helper">먼저 소셜미디어별 콘텐츠 초안을 만들고, 기사별로 검토한 뒤 필요한 소셜미디어만 게시 준비로 넘기면 됩니다.</p>
          <div class="nav">
            <a class="button ghost" href="/">대시보드로 돌아가기</a>
            {''.join(action_forms)}
          </div>
        </div>
        """

    def _batch_articles_table(self, batch) -> str:
        rows = []
        for package_ref in batch.packages:
            try:
                package = self.workspace.load_package(batch.relative_dir, package_ref.package_dir)
                package_id = package.package_id
                headline = package.article.headline
                section_name = package.article.section_name or "-"
            except Exception:
                package = None
                package_id = package_ref.package_dir
                headline = package_ref.headline or package_ref.package_dir
                section_name = "-"
            params = urlencode({"relative_dir": batch.relative_dir, "package_id": package_id})
            status_chips = "".join(
                self._status_chip_for_batch_article(batch, package, package_ref, platform)
                for platform in supported_platforms()
            )
            rows.append(
                f"""
                <tr>
                  <td><a href="/article?{params}">{escape(headline)}</a></td>
                  <td>{escape(section_name)}</td>
                  <td>{status_chips}</td>
                </tr>
                """
            )
        return f"""
        <div class="panel span-8">
          <div class="eyebrow">기사 목록</div>
          <h2>검토할 기사</h2>
          <table>
            <thead>
              <tr>
                <th>기사</th>
                <th>섹션</th>
                <th>소셜미디어별 상태</th>
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
            status_payload = self.workspace.read_batch_status(batch, platform)
            if status_payload is None:
                items.append(
                    f"<div class='chip warn'>{escape(display_platform_name(platform))}: 아직 상태가 없습니다</div>"
                )
            else:
                state = str(status_payload.get("state") or "unknown")
                items.append(
                    f"<div class='chip {'good' if state in {'approved', 'published'} else 'warn'}'>{escape(display_platform_name(platform))}: {escape(_display_state_label(state))}</div>"
                )
        return f"""
        <div class="panel span-4">
          <div class="eyebrow">진행 상태</div>
          <h2>소셜미디어 상태</h2>
          <div class="stack">{''.join(items)}</div>
        </div>
        """

    def _article_overview_card(self, relative_dir: str, package_id: str) -> str:
        return f"""
        <div class="panel span-12">
          <div class="eyebrow">진행 안내</div>
          <div class="section-title">
            <h2>검토 후 게시 준비</h2>
            <a class="muted-link" href="/actions/approve?{urlencode({'relative_dir': relative_dir, 'package_id': package_id})}">승인 안내</a>
          </div>
          <p class="helper">이 화면에서는 소셜미디어별 콘텐츠 초안을 보고 승인 또는 보류를 정합니다. 승인된 콘텐츠만 게시 준비 단계로 넘어갑니다.</p>
          <div class="meta">
            <span>기사 묶음: {escape(relative_dir)}</span>
            <span>기사 ID: {escape(package_id)}</span>
            <span>흐름: 기사 -> 콘텐츠 초안 -> 승인 -> 게시 준비</span>
          </div>
        </div>
        """

    def _platform_review_card(self, batch, package, platform: str) -> str:
        approval_payload = self.workspace.read_approval(batch.relative_dir, package.package_id)
        decision = None if approval_payload is None else approval_payload.get("platforms", {}).get(platform)
        status_payload = self.workspace.read_article_status(batch, package, platform)

        draft_preview_blocks = []
        for artifact_name in artifact_filenames(platform):
            artifact_text = self.workspace.read_review_artifact(batch.relative_dir, package.package_id, artifact_name)
            if artifact_text is not None:
                draft_preview_blocks.append(
                    f"<div class='stack'><div class='chip'>{escape(_display_artifact_name(artifact_name))}</div><pre>{escape(artifact_text)}</pre></div>"
                )

        if not draft_preview_blocks:
            draft_preview_blocks.append("<div class='empty'>아직 검토용 콘텐츠 초안이 없습니다.</div>")

        approval_markup = "<div class='chip warn'>아직 승인 전</div>"
        if decision is not None:
            approval_markup = (
                f"<div class='chip {'good' if decision.get('approved') else 'blocked'}'>{escape('승인됨' if decision.get('approved') else '보류됨')} · {escape(str(decision.get('decided_by') or '알 수 없음'))}</div>"
            )
        status_markup = ""
        if status_payload is not None:
            status_markup = f"<div class='chip'>{escape(_display_state_label(str(status_payload.get('state', 'unknown'))))}</div>"

        form_markup = ""
        if self.workspace.has_approval_root:
            form_markup = self.approval_input.render_form(
                relative_dir=batch.relative_dir,
                package_id=package.package_id,
                article_idxno=package.article.idxno,
                platform=platform,
            )

        return f"""
        <div class="panel span-6" id="platform-{escape(platform)}">
          <div class="eyebrow">{escape(display_platform_name(platform))}</div>
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

    def _status_chip_for_batch_article(self, batch, package, package_ref, platform: str) -> str:
        if package is None:
            status_payload = None
        else:
            status_payload = self.workspace.read_article_status(batch, package, platform)
        if status_payload is None:
            return f"<span class='chip'>{escape(display_platform_name(platform))}: 대기</span>"
        state = str(status_payload.get("state") or "unknown")
        cls = "chip"
        if state in {"approved", "published"}:
            cls += " good"
        elif state in {"blocked", "failed"}:
            cls += " blocked"
        else:
            cls += " warn"
        return f"<span class='{cls}'>{escape(display_platform_name(platform))}: {escape(_display_state_label(state))}</span>"

    def _handle_build_review_all(self, environ, start_response):
        form = self._post(environ)
        relative_dir = form.get("relative_dir", "")
        if not self.workspace.has_review_root:
            return self._redirect(
                start_response,
                f"/batch?{urlencode({'relative_dir': relative_dir, 'flash': '콘텐츠 초안을 저장할 경로가 아직 연결되지 않았습니다.'})}",
            )
        summary = self.workspace.build_review_all(relative_dir)
        message = f"{summary['platform_count']}개 소셜미디어용 콘텐츠 초안을 만들었습니다."
        return self._redirect(start_response, f"/batch?{urlencode({'relative_dir': relative_dir, 'flash': message})}")

    def _handle_approve(self, environ, start_response):
        form = self._post(environ)
        relative_dir = form.get("relative_dir", "")
        package_id = form.get("package_id", "")
        if not self.workspace.has_approval_root:
            return self._redirect(
                start_response,
                f"/article?{urlencode({'relative_dir': relative_dir, 'package_id': package_id, 'flash': '승인 정보를 저장할 경로가 아직 연결되지 않았습니다.'})}",
            )
        try:
            submission = self.approval_input.parse_submission(form)
        except ApprovalInputError as exc:
            return self._redirect(
                start_response,
                f"/article?{urlencode({'relative_dir': relative_dir, 'package_id': package_id, 'flash': str(exc)})}",
            )
        self.workspace.submit_approval(submission)
        message = self.approval_input.success_message(submission)
        return self._redirect(start_response, f"/article?{urlencode({'relative_dir': relative_dir, 'package_id': package_id, 'flash': message})}")

    def _handle_create_publish_requests(self, environ, start_response):
        form = self._post(environ)
        relative_dir = form.get("relative_dir", "")
        platform = form.get("platform", "")
        if not self.workspace.has_review_root or not self.workspace.has_outbox_root:
            return self._redirect(
                start_response,
                f"/batch?{urlencode({'relative_dir': relative_dir, 'flash': '콘텐츠 초안 저장 경로 또는 게시 준비 경로가 아직 연결되지 않았습니다.'})}",
            )
        summary = self.workspace.create_publish_requests(relative_dir, platform)
        message = (
            f"{display_platform_name(platform)}용 콘텐츠 {summary['request_count']}건을 "
            "게시 준비 상태로 넘겼습니다."
        )
        return self._redirect(start_response, f"/batch?{urlencode({'relative_dir': relative_dir, 'flash': message})}")


def _display_state_label(state: str) -> str:
    labels = {
        "received": "받음",
        "building": "만드는 중",
        "built": "초안 생성 완료",
        "review_required": "검토 필요",
        "approved": "승인됨",
        "publishing": "게시 준비 중",
        "published": "게시 완료",
        "blocked": "보류",
        "failed": "실패",
        "skipped": "건너뜀",
        "ready_to_publish": "게시 가능",
        "awaiting_review": "검토 대기",
        "awaiting_platform_approval": "승인 대기",
        "blocked_missing_review_draft": "초안 없음",
        "unknown": "상태 미확인",
    }
    return labels.get(state, state)


def _display_root_label(label: str) -> str:
    labels = {
        "Mode": "연결 방식",
        "Inbox": "기사 보관함",
        "Review": "콘텐츠 초안",
        "Approval": "승인 기록",
        "Outbox": "게시 준비함",
        "Status": "진행 상태",
    }
    return labels.get(label, label)


def _display_root_value(value: str | None) -> str:
    if value in {None, "", "not set"}:
        return "미설정"
    if value == "local filesystem":
        return "로컬 파일"
    if value == "onedrive remote":
        return "원격 OneDrive"
    return value


def _display_approval_store_label(store_kind: str) -> str:
    labels = {
        "local_json": "로컬 JSON 파일",
        "remote_json": "원격 JSON 파일",
        "not configured": "미설정",
    }
    return labels.get(store_kind, store_kind)


def _display_change_type_label(change_type: str | None) -> str:
    labels = {
        "created": "새로 들어온 기사",
        "updated": "수정된 기사",
        "recent_backfill": "테스트용으로 다시 불러온 기사",
        "backfill_recent": "테스트용으로 다시 불러온 기사",
    }
    if not change_type:
        return "변경된 기사"
    return labels.get(change_type, change_type)


def _display_batch_mode_label(mode: str | None) -> str:
    labels = {
        "daily": "일간 백업",
        "monthly": "월간 백업",
        "recent_backfill": "최근 기사 테스트",
        "backfill_recent": "최근 기사 테스트",
    }
    if not mode:
        return "일반"
    return labels.get(mode, mode)


def _display_artifact_name(artifact_name: str) -> str:
    labels = {
        "threads_post.txt": "스레드용 글",
        "x_post.txt": "X용 글",
        "facebook_post.txt": "페이스북용 글",
        "instagram_caption.txt": "인스타그램용 캡션",
        "youtube_title.txt": "유튜브 쇼츠 제목",
        "youtube_description.txt": "유튜브 쇼츠 설명",
        "youtube_script.txt": "유튜브 쇼츠 대본",
        "youtube_storyboard.txt": "유튜브 쇼츠 구성안",
        "youtube_scenes.json": "유튜브 쇼츠 장면 데이터",
    }
    return labels.get(artifact_name, artifact_name)
