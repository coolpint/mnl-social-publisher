from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from html import escape

from .models import ApprovalSubmission
from .platforms import display_platform_name


class ApprovalInputError(ValueError):
    pass


class BaseApprovalInputHandler(ABC):
    handler_id = "base"
    label = "기본 승인 입력"

    @abstractmethod
    def parse_submission(self, form: Mapping[str, str]) -> ApprovalSubmission:
        raise NotImplementedError

    @abstractmethod
    def render_form(
        self,
        *,
        relative_dir: str,
        package_id: str,
        article_idxno: int,
        platform: str,
    ) -> str:
        raise NotImplementedError

    def success_message(self, submission: ApprovalSubmission) -> str:
        platform_label = display_platform_name(submission.platform)
        action_label = "승인" if submission.approved else "보류"
        return f"{platform_label} 콘텐츠를 {action_label}했습니다."


class WebFormApprovalInputHandler(BaseApprovalInputHandler):
    handler_id = "web_form"
    label = "브라우저 승인 입력"

    def parse_submission(self, form: Mapping[str, str]) -> ApprovalSubmission:
        relative_dir = str(form.get("relative_dir") or "").strip()
        package_id = str(form.get("package_id") or "").strip()
        platform = str(form.get("platform") or "").strip()
        decision = str(form.get("decision") or "").strip().lower()
        decided_by = str(form.get("decided_by") or "").strip() or "operator"
        note = str(form.get("note") or "").strip()
        article_idxno_raw = str(form.get("article_idxno") or "0").strip()

        if not relative_dir:
            raise ApprovalInputError("기사 묶음 경로가 필요합니다.")
        if not package_id:
            raise ApprovalInputError("기사 ID가 필요합니다.")
        if not platform:
            raise ApprovalInputError("소셜미디어 종류가 필요합니다.")
        if decision not in {"approve", "reject"}:
            raise ApprovalInputError("승인 또는 보류 중 하나를 선택해주세요.")
        try:
            article_idxno = int(article_idxno_raw)
        except ValueError as exc:
            raise ApprovalInputError("기사 번호 형식이 올바르지 않습니다.") from exc

        return ApprovalSubmission(
            relative_dir=relative_dir,
            package_id=package_id,
            article_idxno=article_idxno,
            platform=platform,
            approved=(decision == "approve"),
            decided_by=decided_by,
            note=note,
            input_method=self.handler_id,
        )

    def render_form(
        self,
        *,
        relative_dir: str,
        package_id: str,
        article_idxno: int,
        platform: str,
    ) -> str:
        return f"""
        <form class="stack" method="post" action="/actions/approve">
          <input type="hidden" name="relative_dir" value="{escape(relative_dir)}">
          <input type="hidden" name="package_id" value="{escape(package_id)}">
          <input type="hidden" name="article_idxno" value="{article_idxno}">
          <input type="hidden" name="platform" value="{escape(platform)}">
          <input type="text" name="decided_by" placeholder="검토자 이름 또는 이메일">
          <textarea name="note" placeholder="메모를 남겨두면 나중에 보기 쉽습니다"></textarea>
          <div class="nav">
            <button class="primary" type="submit" name="decision" value="approve">승인</button>
            <button type="submit" name="decision" value="reject">보류</button>
          </div>
        </form>
        """


def default_approval_input_handler() -> BaseApprovalInputHandler:
    return WebFormApprovalInputHandler()
