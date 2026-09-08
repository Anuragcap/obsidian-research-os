#!/usr/bin/env python3
"""A small, calm GUI focus timer for Obsidian Research OS."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import time
import tkinter as tk
from tkinter import messagebox

from vault_ops import append_focus


BACKGROUND = "#0B1020"
CARD = "#151D33"
CARD_BORDER = "#263252"
TEXT = "#F5F7FF"
MUTED = "#9AA7C5"
ACCENT = "#8B9CFF"
ACCENT_DARK = "#29345F"
SUCCESS = "#54D6A1"
BUTTON = "#242E4B"
BUTTON_ACTIVE = "#344166"
RING_TRACK = "#202A46"


def format_seconds(seconds: float) -> str:
    """Format remaining time without showing a negative countdown."""
    total = max(0, math.ceil(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def rounded_rectangle(canvas: tk.Canvas, coords: tuple[int, int, int, int], radius: int, **kwargs: object) -> int:
    """Draw a rounded rectangle using Tkinter's smoothed polygon primitive."""
    x1, y1, x2, y2 = coords
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


class FocusTimer:
    """One task, one timer, and only the controls needed during focus."""

    def __init__(self, vault: Path, minutes: int, task: str) -> None:
        self.vault = vault
        self.planned_minutes = minutes
        self.total_seconds = minutes * 60
        self.task = task
        self.remaining = float(self.total_seconds)
        self.active_seconds = 0.0
        self.running = True
        self.last_tick = time.monotonic()
        self.logged = False

        self.root = tk.Tk()
        self.root.title("Focus · Obsidian Research OS")
        self.root.configure(bg=BACKGROUND)
        self.root.resizable(False, False)
        # The task card, timer ring, controls, and shortcut hint need a little
        # more vertical room than the original compact window provided.
        self.root.geometry("460x650")
        self.root.minsize(460, 650)
        self.root.protocol("WM_DELETE_WINDOW", self.cancel)
        self.root.bind("<space>", self.toggle_pause_event)
        self.root.bind("p", self.toggle_pause_event)
        self.root.bind("P", self.toggle_pause_event)
        self.root.bind("<Return>", self.finish_event)
        self.root.bind("<Escape>", self.cancel_event)
        self._center_window()
        self._build()
        self.root.after(100, self.tick)

    def _center_window(self) -> None:
        self.root.update_idletasks()
        width, height = 460, 650
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build(self) -> None:
        outer = tk.Frame(self.root, bg=BACKGROUND, padx=30, pady=28)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=BACKGROUND)
        header.pack(fill="x")
        tk.Label(
            header, text="OBSIDIAN RESEARCH OS", bg=BACKGROUND, fg=ACCENT,
            font=("TkDefaultFont", 9, "bold"),
        ).pack(side="left")
        self.mode_label = tk.Label(
            header, text="●  IN FOCUS", bg=BACKGROUND, fg=SUCCESS,
            font=("TkDefaultFont", 9, "bold"),
        )
        self.mode_label.pack(side="right")

        tk.Label(
            outer, text="Make space for one thing.", bg=BACKGROUND, fg=TEXT,
            anchor="w", font=("TkDefaultFont", 20, "bold"), pady=18,
        ).pack(fill="x")

        task_card = tk.Canvas(outer, height=80, bg=BACKGROUND, highlightthickness=0)
        task_card.pack(fill="x", pady=(0, 16))
        rounded_rectangle(task_card, (1, 1, 398, 78), 16, fill=CARD, outline=CARD_BORDER, width=1)
        task_card.create_text(20, 21, text="CURRENT TASK", anchor="w", fill=MUTED, font=("TkDefaultFont", 8, "bold"))
        task_card.create_text(20, 50, text=self.task, anchor="w", fill=TEXT, width=350, font=("TkDefaultFont", 12), justify="left")

        self.ring = tk.Canvas(outer, width=260, height=260, bg=BACKGROUND, highlightthickness=0)
        self.ring.pack(pady=(0, 8))
        self.ring.create_oval(18, 18, 242, 242, outline=RING_TRACK, width=12)
        self.progress_arc = self.ring.create_arc(
            18, 18, 242, 242, start=90, extent=-360, style="arc", outline=ACCENT, width=12,
        )
        self.clock = self.ring.create_text(
            130, 116, text=format_seconds(self.remaining), fill=TEXT,
            font=("TkFixedFont", 42, "bold"),
        )
        self.ring.create_text(130, 157, text="remaining", fill=MUTED, font=("TkDefaultFont", 10))

        self.status = tk.Label(
            outer, text="Stay with the task. The rest can wait.", bg=BACKGROUND, fg=MUTED,
            font=("TkDefaultFont", 10), pady=7,
        )
        self.status.pack()

        controls = tk.Frame(outer, bg=BACKGROUND)
        controls.pack(pady=(12, 11))
        self.pause_button = self._button(controls, "Pause", BUTTON, BUTTON_ACTIVE, self.toggle_pause)
        self.pause_button.pack(side="left", padx=(0, 10))
        self.finish_button = self._button(controls, "Finish session", SUCCESS, "#78E5B8", self.finish, dark_text=True)
        self.finish_button.pack(side="left")

        tk.Label(
            outer, text="Space / P  pause     Enter  finish     Esc  cancel", bg=BACKGROUND, fg="#647190",
            font=("TkDefaultFont", 8), pady=5,
        ).pack()

    def _button(self, parent: tk.Widget, text: str, color: str, active: str, command: object, dark_text: bool = False) -> tk.Button:
        foreground = BACKGROUND if dark_text else TEXT
        return tk.Button(
            parent, text=text, command=command, bg=color, fg=foreground,
            activebackground=active, activeforeground=foreground, relief="flat",
            borderwidth=0, font=("TkDefaultFont", 10, "bold"), padx=18, pady=11,
            cursor="hand2", takefocus=False,
        )

    def _refresh_timer(self) -> None:
        progress = max(0.0, min(1.0, self.remaining / self.total_seconds))
        self.ring.itemconfigure(self.clock, text=format_seconds(self.remaining))
        self.ring.itemconfigure(self.progress_arc, extent=-360 * progress)

    def tick(self) -> None:
        now = time.monotonic()
        if self.running:
            elapsed = now - self.last_tick
            self.remaining -= elapsed
            self.active_seconds += elapsed
            self._refresh_timer()
            if self.remaining <= 0:
                self.finish(completed=True)
                return
        self.last_tick = now
        self.root.after(100, self.tick)

    def toggle_pause_event(self, _event: tk.Event[tk.Misc]) -> None:
        self.toggle_pause()

    def toggle_pause(self) -> None:
        self.running = not self.running
        self.last_tick = time.monotonic()
        if self.running:
            self.pause_button.configure(text="Pause")
            self.mode_label.configure(text="●  IN FOCUS", fg=SUCCESS)
            self.status.configure(text="Stay with the task. The rest can wait.")
        else:
            self.pause_button.configure(text="Resume")
            self.mode_label.configure(text="Ⅱ  PAUSED", fg=ACCENT)
            self.status.configure(text="Take a breath. Resume when you are ready.")

    def finish_event(self, _event: tk.Event[tk.Misc]) -> None:
        self.finish()

    def finish(self, completed: bool = False) -> None:
        if self.logged:
            return
        if not completed and not messagebox.askyesno(
            "Finish focus session", "Log the time you have focused so far?", parent=self.root
        ):
            return
        minutes = self.planned_minutes if completed else max(1, math.ceil(self.active_seconds / 60))
        daily_note = self.vault / "Daily" / f"{time.strftime('%Y-%m-%d')}.md"
        try:
            append_focus(daily_note, minutes, self.task)
        except (OSError, SystemExit) as error:
            messagebox.showerror("Could not log session", str(error), parent=self.root)
            return
        self.logged = True
        self.root.destroy()

    def cancel_event(self, _event: tk.Event[tk.Misc]) -> None:
        self.cancel()

    def cancel(self) -> None:
        if messagebox.askyesno("Cancel focus session", "Close without logging this session?", parent=self.root):
            self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small Obsidian Research OS focus timer.")
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--minutes", type=int, default=25)
    parser.add_argument("--task", default="Focused work")
    args = parser.parse_args()
    if not 1 <= args.minutes <= 240:
        parser.error("--minutes must be between 1 and 240")
    daily_note = args.vault / "Daily" / f"{time.strftime('%Y-%m-%d')}.md"
    if not daily_note.exists():
        parser.error("today's Daily note does not exist; run obs today first")
    FocusTimer(args.vault, args.minutes, args.task).run()


if __name__ == "__main__":
    main()
