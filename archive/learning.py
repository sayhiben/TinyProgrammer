import os
import random
from typing import Optional


DEFAULT_HEADER = "# Developer Journal"


def _default_filepath() -> str:
    try:
        import config
        return getattr(config, "LEARNING_JOURNAL_PATH")
    except Exception:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, "lessons.md")


class LearningSystem:
    """
    Manages the 'long-term memory' of the Tiny Programmer.
    Stores lessons learned from successes and failures.
    """
    
    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or _default_filepath()
        self._ensure_file()

    def _write_path(self) -> str:
        return os.path.realpath(self.filepath)

    def _ensure_file(self):
        path = self._write_path()
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        if not os.path.exists(path) or os.path.getsize(path) == 0:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"{DEFAULT_HEADER}\n\n")

    def add_lesson(self, lesson: str, max_lessons=50):
        """
        Add a new lesson to the journal.
        Keeps file size limited to max_lessons (FIFO), preserving header.
        """
        # Clean up lesson
        lesson = lesson.strip().replace("\n", " ")
        if not lesson:
            return False

        path = self._write_path()

        # Read existing content
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        else:
            lines = [f"{DEFAULT_HEADER}\n", "\n"]

        # Separate header and lessons
        header = []
        lessons = []
        for line in lines:
            if line.startswith("- "):
                lessons.append(line.rstrip("\n"))
            elif line.strip():
                header.append(line.rstrip("\n"))

        if not header:
            header = [DEFAULT_HEADER]

        # Add new lesson
        lessons.append(f"- {lesson}")

        # Truncate if too many (keep most recent)
        if len(lessons) > max_lessons:
            lessons = lessons[-max_lessons:]

        # Write back
        with open(path, "w", encoding="utf-8") as f:
            for line in header:
                f.write(f"{line}\n")
            f.write("\n")
            for line in lessons:
                f.write(f"{line}\n")

        return True

    def get_recent_lessons(self, limit=5) -> str:
        """Get the most recent lessons formatted for a prompt."""
        path = self._write_path()
        if not os.path.exists(path):
            return ""

        with open(path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.startswith("-")]

        if not lines:
            return ""

        # Get random selection from recent history to avoid staleness
        # taking last 20, picking 'limit' random ones
        candidates = lines[-20:]
        if len(candidates) > limit:
            selected = random.sample(candidates, limit)
        else:
            selected = candidates

        return "\n".join(selected)
