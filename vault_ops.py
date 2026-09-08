#!/usr/bin/env python3
"""Safe, dependency-free edits for Obsidian Research OS Daily notes."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path
import re
import sys


# The normal form is a standalone ``## Tasks`` heading.  The second branch
# also reads notes where a checklist was accidentally joined to the heading
# (``## Tasks- [ ] …``), so existing work remains accessible and can be
# repaired rather than appearing to disappear.
TASK_SECTION = re.compile(
    r"^## Tasks(?:[ \t]*$|(?=- \[[ xX]\][ \t]))([\s\S]*?)(?=^## |\Z)",
    re.M,
)


def normalize_task_heading(text: str) -> str:
    """Restore the newline between a Tasks heading and an attached checkbox."""
    return re.sub(r"(?m)^(## Tasks)(?=- \[[ xX]\][ \t])", r"\1\n", text)


def atomic_write(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text)
    temporary.replace(path)


def refresh_index(vault: Path, kind: str) -> Path:
    """Refresh one generated index block while preserving user-written content."""
    if kind == "daily":
        title = "Daily Notes"
        index_path = vault / "Daily Notes.md"
        start_marker = "<!-- OBS:DAILY-INDEX:START -->"
        end_marker = "<!-- OBS:DAILY-INDEX:END -->"
        notes = sorted((vault / "Daily").glob("????-??-??.md"), reverse=True)
        links = [f"- [[Daily/{note.stem}]]" for note in notes]
    else:
        title = "Paper Notes"
        index_path = vault / "Paper Notes.md"
        start_marker = "<!-- OBS:PAPER-INDEX:START -->"
        end_marker = "<!-- OBS:PAPER-INDEX:END -->"
        papers = sorted(
            (path for path in (vault / "Research" / "Papers").rglob("*.md") if path.is_file()),
            key=lambda path: path.relative_to(vault).as_posix().casefold(),
        )
        links = [f"- [[{note.relative_to(vault).with_suffix('').as_posix()}]]" for note in papers]

    body = "\n".join(links) if links else "- No notes yet."
    generated = f"{start_marker}\n\n## All {title}\n\n{body}\n\n{end_marker}"
    if index_path.exists():
        text = index_path.read_text()
        pattern = re.compile(rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}", re.S)
        text = pattern.sub(generated, text, count=1) if pattern.search(text) else text.rstrip() + "\n\n" + generated + "\n"
    else:
        text = f"---\ntype: index\n---\n\n# {title}\n\n{generated}\n"
    atomic_write(index_path, text)
    return index_path


def refresh_indexes(vault: Path, kind: str) -> list[Path]:
    kinds = ("daily", "papers") if kind == "all" else (kind,)
    return [refresh_index(vault, item) for item in kinds]


def task_section(text: str) -> re.Match[str]:
    match = TASK_SECTION.search(text)
    if not match:
        raise SystemExit("ERROR: ## Tasks section not found.")
    return match


def open_tasks(section: str) -> list[tuple[int, str]]:
    tasks = []
    for line_number, line in enumerate(section.splitlines(), 1):
        if line.startswith("- [ ] "):
            tasks.append((line_number, line[6:].strip()))
    # `!` means important. It is deliberately a convention, not metadata.
    return sorted(tasks, key=lambda item: (not item[1].startswith("!"), item[0]))


def list_tasks(path: Path) -> None:
    match = task_section(path.read_text())
    tasks = open_tasks(match.group(1))
    if not tasks:
        print("No open tasks for today.")
        return
    print("Today's open tasks:")
    for number, (_, task) in enumerate(tasks, 1):
        due = re.search(r"📅 (\d{4}-\d{2}-\d{2})", task)
        label = ""
        if due:
            try:
                due_day = date.fromisoformat(due.group(1))
                label = " [overdue]" if due_day < date.today() else " [due today]" if due_day == date.today() else ""
            except ValueError:
                pass
        print(f"  {number}. {task}{label}")


def next_task(path: Path) -> None:
    """Show the first task using the same important-first order as task list."""
    tasks = open_tasks(task_section(path.read_text()).group(1))
    if not tasks:
        print("No open tasks for today.")
        return
    print(f"Next task: {tasks[0][1]}")


def daily_streak(vault: Path) -> None:
    """Report current and longest streaks from date-named Daily notes."""
    days = []
    for path in (vault / "Daily").glob("????-??-??.md"):
        try:
            days.append(date.fromisoformat(path.stem))
        except ValueError:
            continue
    days = sorted(set(days))
    if not days:
        print("Daily note streak: 0 days. Create a Daily note to begin.")
        return
    longest = run = 1
    for previous, current in zip(days, days[1:]):
        run = run + 1 if current == previous + timedelta(days=1) else 1
        longest = max(longest, run)
    today_run = 0
    cursor = date.today()
    known = set(days)
    while cursor in known:
        today_run += 1
        cursor -= timedelta(days=1)
    print(f"Daily note streak: {today_run} day(s) current · {longest} day(s) longest")


def add_task(path: Path, task: str) -> None:
    text = normalize_task_heading(path.read_text())
    match = task_section(text)
    section = match.group(1)
    retained = [line for line in section.splitlines() if line.strip() != "- [ ]"]
    # Keep the newline that separates the heading from its first task.  Using
    # ``strip()`` here used to remove it, producing ``## Tasks- [ ] …`` after
    # the second task was added.
    body = "\n".join(retained).rstrip()
    if body:
        body = ("" if body.startswith("\n") else "\n") + body + "\n"
    else:
        body = "\n"
    body += f"- [ ] {task}\n"
    atomic_write(path, text[: match.start(1)] + body + text[match.end(1) :])
    print("Added task to today's Daily note.")


def add_due_task(path: Path, due: date, task: str) -> None:
    """Add a task with a portable, readable Markdown due-date marker."""
    add_task(path, f"{task} 📅 {due.isoformat()}")


def done_task(path: Path, number: int) -> None:
    text = normalize_task_heading(path.read_text())
    match = task_section(text)
    section = match.group(1)
    tasks = open_tasks(section)
    if not 1 <= number <= len(tasks):
        raise SystemExit("ERROR: Invalid task number. Run 'obs tasks' and try again.")
    line_number, task = tasks[number - 1]
    lines = section.splitlines(keepends=True)
    index = line_number - 1
    lines[index] = lines[index].replace("- [ ] ", "- [x] ", 1)
    atomic_write(path, text[: match.start(1)] + "".join(lines) + text[match.end(1) :])
    print(f"Completed: {task}")


def delete_task(path: Path, number: int) -> None:
    """Permanently remove one open task selected by its displayed number."""
    text = normalize_task_heading(path.read_text())
    match = task_section(text)
    section = match.group(1)
    tasks = open_tasks(section)
    if not 1 <= number <= len(tasks):
        raise SystemExit("ERROR: Invalid task number. Run 'obs tasks' and try again.")
    line_number, task = tasks[number - 1]
    lines = section.splitlines(keepends=True)
    del lines[line_number - 1]
    atomic_write(path, text[: match.start(1)] + "".join(lines) + text[match.end(1) :])
    print(f"Deleted: {task}")


def add_tasks(text: str, additions: list[str]) -> str:
    """Append checklist entries while preserving the Tasks-heading newline."""
    match = task_section(text)
    section = match.group(1)
    retained = [line for line in section.splitlines() if line.strip() != "- [ ]"]
    body = "\n".join(retained).rstrip()
    if body:
        body = ("" if body.startswith("\n") else "\n") + body + "\n"
    else:
        body = "\n"
    body += "".join(f"- [ ] {task}\n" for task in additions)
    return text[: match.start(1)] + body + text[match.end(1) :]


def record_carry_forward(text: str, carried: list[str]) -> str:
    """Keep a small history in the source note's Carry Forward section."""
    heading = re.search(r"^### Carry Forward[ \t]*$", text, re.M)
    if not heading:
        return text
    end = re.search(r"^#{2,3} |^<!-- CLOSE:END -->", text[heading.end() :], re.M)
    stop = heading.end() + (end.start() if end else len(text[heading.end() :]))
    existing = [
        line[2:].strip()
        for line in text[heading.end() : stop].splitlines()
        if line.startswith("- ") and line[2:].strip() not in ("", "None", "-")
    ]
    entries = list(dict.fromkeys(existing + carried))
    replacement = "\n\n" + ("\n".join(f"- {task}" for task in entries) or "-") + "\n"
    return text[: heading.end()] + replacement + text[stop:]


def transfer_tasks(source: Path, target: Path, selection: str) -> list[str]:
    """Move selected unchecked tasks between Daily notes and return their text."""
    text = normalize_task_heading(source.read_text())
    match = task_section(text)
    available = open_tasks(match.group(1))
    if selection.lower() == "all":
        numbers = set(range(1, len(available) + 1))
    else:
        try:
            numbers = {int(value.strip()) for value in selection.split(",")}
        except ValueError as error:
            raise SystemExit("ERROR: Use 'all' or task numbers such as 1,3.") from error
        if not numbers or any(number < 1 or number > len(available) for number in numbers):
            raise SystemExit("ERROR: One or more task numbers are invalid.")
    carried = [task for number, (_, task) in enumerate(available, 1) if number in numbers]
    source_lines = match.group(1).splitlines(keepends=True)
    selected_lines = {available[number - 1][0] for number in numbers}
    section = "".join(line for index, line in enumerate(source_lines, 1) if index not in selected_lines)
    text = text[: match.start(1)] + section + text[match.end(1) :]
    atomic_write(source, record_carry_forward(text, carried))

    target_text = normalize_task_heading(target.read_text()) if target.exists() else daily_skeleton(date.fromisoformat(target.stem))
    atomic_write(target, add_tasks(target_text, carried))
    return carried


def rollover(vault: Path, day: date) -> None:
    """Non-interactively move every open task from yesterday into ``day``."""
    source = vault / "Daily" / f"{day - timedelta(days=1):%Y-%m-%d}.md"
    if not source.exists():
        return
    available = open_tasks(task_section(source.read_text()).group(1))
    if not available:
        return
    target = vault / "Daily" / f"{day:%Y-%m-%d}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    carried = transfer_tasks(source, target, "all")
    print(f"Carried {len(carried)} unfinished task(s) from {source.stem} into {target.stem}.")


def recover_overdue(vault: Path, day: date) -> None:
    """Prompt for unfinished tasks from Daily notes older than yesterday."""
    daily = vault / "Daily"
    if not daily.exists():
        return
    target = daily / f"{day:%Y-%m-%d}.md"
    for source in sorted(daily.glob("????-??-??.md")):
        try:
            source_day = date.fromisoformat(source.stem)
        except ValueError:
            continue
        if source_day >= day:
            continue
        available = open_tasks(task_section(source.read_text()).group(1))
        if not available:
            continue
        print(f"\nUnfinished tasks from {source_day:%A, %-d %B %Y}:")
        for number, (_, task) in enumerate(available, 1):
            print(f"  {number}. {task}")
        try:
            selection = input("Carry forward [all | 1,3 | Enter to leave here]: ").strip()
        except EOFError:
            print("\nNo selection received; leaving these tasks in their original note.")
            continue
        if not selection:
            continue
        carried = transfer_tasks(source, target, selection)
        print(f"Carried {len(carried)} task(s) into {target.stem}.")


def append_skill(path: Path, heading: str, entry: str) -> None:
    text = path.read_text()
    if not re.search(r"^## Skill Log\s*$", text, re.M):
        insert = "\n\n## Skill Log\n\n### Chess\n\n### Typing\n\n### Other Skills\n"
        end = re.search(r"^## End of Day\s*$", text, re.M)
        text = text[: end.start()] + insert + "\n" + text[end.start() :] if end else text.rstrip() + insert
    match = re.search(rf"^{re.escape(heading)}\s*$", text, re.M)
    if not match:
        raise SystemExit(f"ERROR: {heading} section not found.")
    next_heading = re.search(r"^#{2,3} ", text[match.end() :], re.M)
    position = match.end() + (next_heading.start() if next_heading else len(text[match.end() :]))
    text = text[:position].rstrip() + f"\n- {entry}\n\n" + text[position:].lstrip("\n")
    atomic_write(path, text)


def append_focus(path: Path, minutes: int, task: str) -> None:
    """Record a completed focus block in a Daily note."""
    text = path.read_text()
    entry = f"- {datetime.now():%H:%M} · {minutes} min · {task}"
    heading = re.search(r"^## Focus\s*$", text, re.M)
    if not heading:
        before = re.search(r"^## Skill Log\s*$|^## End of Day\s*$", text, re.M)
        position = before.start() if before else len(text)
        text = text[:position].rstrip() + "\n\n## Focus\n\n" + entry + "\n\n" + text[position:].lstrip("\n")
    else:
        next_heading = re.search(r"^## ", text[heading.end() :], re.M)
        position = heading.end() + (next_heading.start() if next_heading else len(text[heading.end() :]))
        text = text[:position].rstrip() + "\n" + entry + "\n\n" + text[position:].lstrip("\n")
    atomic_write(path, text)
    print(f"Logged {minutes}-minute focus session.")


def daily_skeleton(day: date) -> str:
    return f"""---
type: daily
date: {day:%Y-%m-%d}
---

# {day:%A}, {day.day} {day:%B} {day:%Y}

## Calendar

<!-- CALENDAR:START -->
<!-- CALENDAR:END -->

## Tasks

- [ ]

## Research

-

## Notes

-

## Inbox / Ideas

-

## Focus

-

## Skill Log

### Chess

### Typing

### Other Skills

## End of Day

<!-- CLOSE:START -->
### Reflection

- Win:
- Lesson:
- Tomorrow's first priority:

### Carry Forward

-
<!-- CLOSE:END -->
"""


def section_bullets(text: str, heading: str, level: int) -> list[str]:
    """Return meaningful top-level bullets below one Markdown heading."""
    match = re.search(rf"^{re.escape('#' * level)} {re.escape(heading)}[ \t]*$", text, re.M)
    if not match:
        return []
    following_heading = re.search(rf"^#{{1,{level}}} ", text[match.end() :], re.M)
    body = text[match.end() : match.end() + following_heading.start() if following_heading else len(text)]
    return [
        item.strip()
        for item in re.findall(r"(?m)^- (.+)$", body)
        if item.strip() not in ("", "-")
    ]


def note_date(path: Path) -> date:
    """Use a note's created field, falling back to its filesystem timestamp."""
    match = re.search(r"(?m)^created:\s*(\d{4}-\d{2}-\d{2})", path.read_text(errors="replace"))
    if match:
        try:
            return date.fromisoformat(match.group(1))
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime).date()


def notes_created_this_week(directory: Path, start: date, end: date) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        (path for path in directory.rglob("*.md") if start <= note_date(path) <= end),
        key=lambda path: path.name.casefold(),
    )


def compact_items(items: list[str], limit: int = 4) -> str:
    """Format a short, readable preview without making review output noisy."""
    shown = items[:limit]
    suffix = f" · +{len(items) - limit} more" if len(items) > limit else ""
    return " · ".join(shown) + suffix


def review_week(vault: Path) -> None:
    today = date.today()
    days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    completed = open_count = carried = 0
    daily_notes = 0
    research_updates: list[tuple[date, str]] = []
    reflection_wins: list[tuple[date, str]] = []
    chess_elos: list[tuple[date, str]] = []
    focus_minutes = 0
    chess_entries: list[str] = []
    typing: list[tuple[str, str]] = []
    other_skills: list[str] = []
    for day in days:
        path = vault / "Daily" / f"{day:%Y-%m-%d}.md"
        if not path.exists():
            continue
        daily_notes += 1
        text = path.read_text()
        completed += len(re.findall(r"(?m)^- \[x\] ", text))
        open_count += len(re.findall(r"(?m)^- \[ \] ", text))
        carried += len(section_bullets(text, "Carry Forward", 3))
        research_updates.extend((day, entry) for entry in section_bullets(text, "Research", 2))
        wins = re.findall(r"(?m)^- Win:[ \t]*(.+)$", text)
        reflection_wins.extend(
            (day, win.strip()) for win in wins if win.strip() not in ("-", "—")
        )
        chess_entries.extend(section_bullets(text, "Chess", 3))
        for elo in re.findall(r"ELO: ([0-9]+)", text):
            chess_elos.append((day, elo))
        typing.extend(re.findall(r"Monkeytype \(([^)]+)\): ([0-9.]+ WPM \| [0-9.]+% accuracy)", text))
        other_skills.extend(section_bullets(text, "Other Skills", 3))
        for minutes in re.findall(r"(?m)^- \d{2}:\d{2} · (\d+) min · ", text):
            focus_minutes += int(minutes)

    concepts = notes_created_this_week(vault / "Research" / "Concepts", days[0], today)
    papers = notes_created_this_week(vault / "Research" / "Papers", days[0], today)
    inbox_dir = vault / "Inbox"
    inbox_captures = notes_created_this_week(inbox_dir, days[0], today)
    inbox_open = list(inbox_dir.glob("*.md")) if inbox_dir.exists() else []

    print(f"Weekly review · {days[0]:%d %b}–{days[-1]:%d %b %Y}")
    print(f"Daily notes: {daily_notes}/7 logged")
    print(f"Tasks: {completed} completed · {open_count} still open · {carried} carried forward")
    if focus_minutes:
        print(f"Focus: {focus_minutes} minutes logged")
    print(f"Research: {len(research_updates)} daily update(s) · {len(concepts)} concept(s) created · {len(papers)} paper note(s) added")
    if research_updates:
        print("Research updates: " + compact_items([f"{day:%a}: {entry}" for day, entry in research_updates]))
    if concepts:
        print("New concepts: " + compact_items([path.stem for path in concepts]))
    if papers:
        print("New papers: " + compact_items([path.stem for path in papers]))
    if chess_entries or typing or other_skills:
        skill_parts = []
        if chess_entries:
            skill_parts.append(f"Chess: {len(chess_entries)} update(s)")
        if typing:
            best_wpm = max(float(result.split(" WPM", 1)[0]) for _, result in typing)
            skill_parts.append(f"Typing: {len(typing)} run(s), best {best_wpm:g} WPM")
        if other_skills:
            skill_parts.append(f"Other: {len(other_skills)} update(s)")
        print("Skills: " + " · ".join(skill_parts))
    if chess_elos:
        print(f"Chess ELO: {chess_elos[0][1]} → {chess_elos[-1][1]}")
    if typing:
        print("Latest Monkeytype: " + typing[-1][1] + f" ({typing[-1][0]})")
    if other_skills:
        print("Other skill updates: " + compact_items(other_skills))
    print(f"Inbox: {len(inbox_captures)} captured this week · {len(inbox_open)} awaiting review")
    if reflection_wins:
        print("Wins: " + compact_items([f"{day:%a}: {win}" for day, win in reflection_wins]))
    print("Next: choose one unfinished priority and one learning target for the coming week.")


def export_week(vault: Path, output: Path) -> None:
    """Write a shareable Markdown snapshot of the current weekly review."""
    report = StringIO()
    with redirect_stdout(report):
        review_week(vault)
    output.parent.mkdir(parents=True, exist_ok=True)
    text = (
        f"# Weekly review · {date.today():%d %b %Y}\n\n"
        "Generated by Obsidian Research OS.\n\n"
        "## Summary\n\n"
        + "\n".join(f"- {line}" for line in report.getvalue().splitlines()[:-1])
        + "\n\n## Next week\n\n- Main priority:\n- Learning target:\n"
    )
    atomic_write(output, text)
    print(f"Exported weekly review: {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("task-add", "task-due", "task-list", "task-next", "task-done", "task-delete", "skill", "focus"):
        item = sub.add_parser(name)
        item.add_argument("path", type=Path)
        if name == "task-add": item.add_argument("text")
        if name == "task-due": item.add_argument("due", type=date.fromisoformat); item.add_argument("text")
        if name == "focus": item.add_argument("minutes", type=int); item.add_argument("text")
        if name in ("task-done", "task-delete"): item.add_argument("number", type=int)
        if name == "skill": item.add_argument("heading"); item.add_argument("entry")
    item = sub.add_parser("review-week")
    item.add_argument("vault", type=Path)
    item = sub.add_parser("streak")
    item.add_argument("vault", type=Path)
    item = sub.add_parser("export-week")
    item.add_argument("vault", type=Path)
    item.add_argument("output", type=Path)
    item = sub.add_parser("index")
    item.add_argument("vault", type=Path)
    item.add_argument("--kind", choices=("daily", "papers", "all"), default="all")
    item.add_argument("--quiet", action="store_true")
    for name in ("rollover", "recover-overdue"):
        item = sub.add_parser(name)
        item.add_argument("vault", type=Path)
        item.add_argument("--date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    if args.command == "task-add": add_task(args.path, args.text)
    elif args.command == "task-due": add_due_task(args.path, args.due, args.text)
    elif args.command == "task-list": list_tasks(args.path)
    elif args.command == "task-next": next_task(args.path)
    elif args.command == "task-done": done_task(args.path, args.number)
    elif args.command == "task-delete": delete_task(args.path, args.number)
    elif args.command == "skill": append_skill(args.path, args.heading, args.entry)
    elif args.command == "focus": append_focus(args.path, args.minutes, args.text)
    elif args.command == "review-week": review_week(args.vault)
    elif args.command == "streak": daily_streak(args.vault)
    elif args.command == "export-week": export_week(args.vault, args.output)
    elif args.command == "index":
        paths = refresh_indexes(args.vault, args.kind)
        if not args.quiet:
            for path in paths:
                print(f"Updated: {path.name}")
    elif args.command == "rollover": rollover(args.vault, args.date)
    else: recover_overdue(args.vault, args.date)


if __name__ == "__main__":
    main()
