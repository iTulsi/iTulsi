from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "update_contributions.py"
SPEC = importlib.util.spec_from_file_location("update_contributions", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ContributionUpdaterTests(unittest.TestCase):
    def test_make_table_formats_merged_and_open_pull_requests(self) -> None:
        pull_requests = [
            {
                "number": 12,
                "title": "Fix | escaping",
                "url": "https://example.com/pr/12",
                "state": "CLOSED",
                "mergedAt": "2026-06-30T10:00:00Z",
                "repository": {"nameWithOwner": "org/project"},
            },
            {
                "number": 13,
                "title": "Add tests",
                "url": "https://example.com/pr/13",
                "state": "OPEN",
                "mergedAt": None,
                "repository": {"nameWithOwner": "org/other"},
            },
        ]

        table = MODULE.make_table(pull_requests)

        self.assertIn(r"Fix \| escaping", table)
        self.assertIn("| Merged |", table)
        self.assertIn("| Open |", table)

    def test_replace_section_preserves_surrounding_content(self) -> None:
        content = (
            "Before\n"
            f"{MODULE.START_MARKER}\nold\n{MODULE.END_MARKER}\n"
            "After\n"
        )

        updated = MODULE.replace_section(content, "new")

        self.assertEqual(
            updated,
            (
                "Before\n"
                f"{MODULE.START_MARKER}\nnew\n{MODULE.END_MARKER}\n"
                "After\n"
            ),
        )

    def test_replace_section_rejects_missing_markers(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly one"):
            MODULE.replace_section("README without markers", "replacement")

    def test_empty_results_have_a_clear_fallback(self) -> None:
        table = MODULE.make_table([])
        self.assertIn("No public pull requests found yet", table)


if __name__ == "__main__":
    unittest.main()
