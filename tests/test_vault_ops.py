from __future__ import annotations

from contextlib import redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import vault_ops


DAILY = """# Daily

## Tasks

- [ ] First task
- [ ] ! Important task

## Research

- Read a useful paper

## Skill Log

### Chess

### Typing

### Other Skills

## End of Day

### Carry Forward

-
"""


class VaultOpsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.vault = Path(self.temp.name)
        (self.vault / "Daily").mkdir()
        self.note = self.vault / "Daily" / f"{date.today():%Y-%m-%d}.md"
        self.note.write_text(DAILY)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_tasks_prioritize_important_and_can_be_completed(self) -> None:
        stream = StringIO()
        with redirect_stdout(stream):
            vault_ops.list_tasks(self.note)
        self.assertIn("1. ! Important task", stream.getvalue())

        vault_ops.done_task(self.note, 1)
        self.assertIn("- [x] ! Important task", self.note.read_text())

    def test_next_task_uses_task_priority(self) -> None:
        stream = StringIO()
        with redirect_stdout(stream):
            vault_ops.next_task(self.note)
        self.assertEqual(stream.getvalue().strip(), "Next task: ! Important task")

    def test_indexes_preserve_surrounding_text(self) -> None:
        index = self.vault / "Daily Notes.md"
        index.write_text("# My notes\n\nA personal introduction.\n")
        vault_ops.refresh_index(self.vault, "daily")
        text = index.read_text()
        self.assertIn("A personal introduction.", text)
        self.assertIn(f"[[Daily/{date.today():%Y-%m-%d}]]", text)

    def test_streak_reports_today(self) -> None:
        stream = StringIO()
        with redirect_stdout(stream):
            vault_ops.daily_streak(self.vault)
        self.assertIn("1 day(s) current", stream.getvalue())

    def test_due_task_and_focus_session_are_logged(self) -> None:
        vault_ops.add_due_task(self.note, date.today(), "Send the draft")
        vault_ops.append_focus(self.note, 25, "Write the draft")
        text = self.note.read_text()
        self.assertIn("Send the draft 📅", text)
        self.assertIn("## Focus", text)
        self.assertIn("25 min · Write the draft", text)

    def test_weekly_export_writes_markdown(self) -> None:
        output = self.vault / "Exports" / "week.md"
        vault_ops.export_week(self.vault, output)
        self.assertIn("# Weekly review", output.read_text())
        self.assertIn("## Next week", output.read_text())


if __name__ == "__main__":
    unittest.main()
