from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from html import escape

from .models import ApprovalSubmission


class ApprovalInputError(ValueError):
    pass


class BaseApprovalInputHandler(ABC):
    handler_id = "base"
    label = "Base approval input"

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
        return (
            f"{submission.platform} "
            f"{'approved' if submission.approved else 'rejected'} via {self.handler_id}."
        )


class WebFormApprovalInputHandler(BaseApprovalInputHandler):
    handler_id = "web_form"
    label = "Browser form approval"

    def parse_submission(self, form: Mapping[str, str]) -> ApprovalSubmission:
        relative_dir = str(form.get("relative_dir") or "").strip()
        package_id = str(form.get("package_id") or "").strip()
        platform = str(form.get("platform") or "").strip()
        decision = str(form.get("decision") or "").strip().lower()
        decided_by = str(form.get("decided_by") or "").strip() or "operator"
        note = str(form.get("note") or "").strip()
        article_idxno_raw = str(form.get("article_idxno") or "0").strip()

        if not relative_dir:
            raise ApprovalInputError("relative_dir is required")
        if not package_id:
            raise ApprovalInputError("package_id is required")
        if not platform:
            raise ApprovalInputError("platform is required")
        if decision not in {"approve", "reject"}:
            raise ApprovalInputError("decision must be approve or reject")
        try:
            article_idxno = int(article_idxno_raw)
        except ValueError as exc:
            raise ApprovalInputError("article_idxno must be an integer") from exc

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
          <input type="text" name="decided_by" placeholder="reviewer name or email">
          <textarea name="note" placeholder="review note"></textarea>
          <div class="nav">
            <button class="primary" type="submit" name="decision" value="approve">Approve</button>
            <button type="submit" name="decision" value="reject">Reject</button>
          </div>
        </form>
        """


def default_approval_input_handler() -> BaseApprovalInputHandler:
    return WebFormApprovalInputHandler()
