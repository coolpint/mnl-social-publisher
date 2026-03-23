from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mnl_social_publisher.builders.registry import get_platform_builder
from mnl_social_publisher.builders.youtube import build_youtube_draft
from mnl_social_publisher.generation_profiles import (
    load_text_generation_profile,
    load_youtube_generation_profile,
)
from mnl_social_publisher.package_loader import load_package
from mnl_social_publisher.prompt_templates import render_prompt_template


FIXTURE_PACKAGE_DIR = (
    Path(__file__).parent
    / "fixtures"
    / "social_inbox"
    / "2026"
    / "03"
    / "14"
    / "run-000123"
    / "article-000143"
)


class GenerationProfilesTestCase(unittest.TestCase):
    def test_load_bundled_text_profile(self) -> None:
        profile = load_text_generation_profile("threads")

        self.assertEqual(profile.profile_id, "threads-issue-brief-v1")
        self.assertEqual(profile.prompt_template, "builders/threads.txt")
        self.assertEqual(profile.story_point_limit, 3)

    def test_load_bundled_youtube_profile(self) -> None:
        profile = load_youtube_generation_profile()

        self.assertEqual(profile.profile_id, "youtube-shorts-news-context-v1")
        self.assertEqual(profile.title_suffix, " | 1분 요약")
        self.assertEqual(profile.scene_labels[0], "hook")

    def test_profile_override_root_changes_builder_behavior(self) -> None:
        package = load_package(FIXTURE_PACKAGE_DIR)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            platform_dir = root / "platforms"
            platform_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "platform": "x",
                "profile_id": "x-custom-v99",
                "version": 99,
                "prompt_template": "builders/x.txt",
                "story_point_limit": 2,
                "character_limit": 120,
                "visual_mode_fallback": "custom_x_mode",
                "extra_hashtags": ["속보"],
                "notes": ["커스텀 X 프로필 테스트"],
                "inspiration_patterns": ["헤드라인 뒤에 두 포인트만 둔다."],
            }
            (platform_dir / "x.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"MNL_SOCIAL_PROFILE_ROOT": str(root)}, clear=False):
                draft = get_platform_builder("x")(package)

            self.assertEqual(draft.profile_id, "x-custom-v99")
            self.assertEqual(draft.profile_version, 99)
            self.assertEqual(draft.visual_mode, "custom_x_mode")
            self.assertIn("#속보", draft.hashtags)

    def test_prompt_template_override_root_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            prompt_path = root / "builders" / "threads.txt"
            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            prompt_path.write_text("OVERRIDE: {headline}\n{point_1}\n", encoding="utf-8")

            with patch.dict(os.environ, {"MNL_SOCIAL_TEMPLATE_ROOT": str(root)}, clear=False):
                rendered = render_prompt_template(
                    "builders/threads.txt",
                    headline="테스트 제목",
                    point_1="첫 번째 포인트",
                )

            self.assertEqual(rendered, "OVERRIDE: 테스트 제목\n첫 번째 포인트")

    def test_youtube_profile_override_changes_draft_shape(self) -> None:
        package = load_package(FIXTURE_PACKAGE_DIR)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            platform_dir = root / "platforms"
            platform_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "platform": "youtube_shorts",
                "profile_id": "youtube-custom-v7",
                "version": 7,
                "script_prompt_template": "builders/youtube_script.txt",
                "description_prompt_template": "builders/youtube_description.txt",
                "story_point_limit": 3,
                "title_limit": 80,
                "title_suffix": " | 테스트 숏츠",
                "hook_suffix": " 지금 보겠습니다.",
                "thumbnail_headline_limit": 18,
                "thumbnail_subheadline_limit": 12,
                "scene_labels": ["hook", "point_1", "point_2", "point_3", "context", "cta"],
                "scene_durations": [4, 6, 6, 6, 7, 5],
                "default_tags": ["테스트", "shorts"],
                "visual_mode_fallback": "custom_kinetic_mode",
                "visual_mode_with_assets": "custom_asset_mode",
                "max_tags": 5,
                "notes": ["커스텀 유튜브 프로필 테스트"],
                "inspiration_patterns": ["커스텀 숏츠 테스트 패턴"],
            }
            (platform_dir / "youtube_shorts.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"MNL_SOCIAL_PROFILE_ROOT": str(root)}, clear=False):
                draft = build_youtube_draft(package)

            self.assertEqual(draft.profile_id, "youtube-custom-v7")
            self.assertEqual(draft.profile_version, 7)
            self.assertTrue(draft.title.endswith(" | 테스트 숏츠"))
            self.assertEqual([scene.duration_seconds for scene in draft.scenes], [4, 6, 6, 6, 7, 5])
            self.assertEqual(draft.visuals_mode, "custom_kinetic_mode")
            self.assertLessEqual(len(draft.thumbnail_headline), 18)


if __name__ == "__main__":
    unittest.main()
