"""
IDE-style generated-code typing helpers.

This module only controls how code is rendered to the terminal. Callers remain
responsible for storing the original generated text.
"""

from collections import Counter
import re
import time
from typing import Callable, Optional


_DEDENT_START_RE = re.compile(r"^(elif|else|except|finally|case)\b")


class CodeTypingHelper:
    """Render generated code while fast-forwarding leading indentation."""

    def __init__(
        self,
        terminal,
        enabled: bool = False,
        delay_func: Optional[Callable[[], float]] = None,
        sleep_func: Callable[[float], None] = time.sleep,
        tick_func: Optional[Callable[[], None]] = None,
        seed_text: str = "",
    ):
        self.terminal = terminal
        self.enabled = enabled
        self.delay_func = delay_func
        self.sleep_func = sleep_func
        self.tick_func = tick_func

        self._pending_indent = ""
        self._current_line = ""
        self._line_start = True
        self._predicted_indent = 0

        self._last_significant_indent = 0
        self._last_significant_line = ""
        self._indent_deltas = Counter()
        self.tab_width = 4

        if seed_text:
            self._seed_context(seed_text)

    def type_text(self, text: str):
        """Type text to the terminal without returning or changing it."""
        if not self.enabled:
            for char in text:
                self._type_char(char)
            return

        for index, char in enumerate(text):
            upcoming_indent = None
            if char == "\n":
                upcoming_indent = self._upcoming_indent(text[index + 1:])
            self._type_enabled_char(char, upcoming_indent=upcoming_indent)

    def finish(self):
        """Resolve any speculative indentation before non-code text is typed."""
        if not self.enabled or not self._line_start:
            return

        if self._pending_indent:
            self._reconcile_indent()
            self._line_start = False
        elif self._predicted_indent:
            self._move_indent(self._predicted_indent, 0)
            self._predicted_indent = 0

    def _type_enabled_char(
        self,
        char: str,
        upcoming_indent: Optional[int] = None,
    ):
        if self._line_start and char in (" ", "\t"):
            self._pending_indent += char
            return

        if self._line_start:
            self._reconcile_indent()
            self._line_start = False

        if char == "\n":
            line_indent = self._indent_columns(self._current_line)
            line_was_significant = self._finish_line(self._current_line)
            if upcoming_indent is not None:
                self._predicted_indent = upcoming_indent
            elif line_was_significant:
                self._predicted_indent = self._predict_next_indent()
            else:
                self._predicted_indent = line_indent
            self._type_char(char, render=self._predicted_indent == 0)
            self._current_line = ""
            self._line_start = True
            self._pending_indent = ""
            if self._predicted_indent:
                self._move_indent(0, self._predicted_indent)
            return

        self._type_char(char)
        self._current_line += char

    def _reconcile_indent(self):
        actual_indent = self._indent_columns(self._pending_indent)
        current_indent = self._predicted_indent

        if current_indent != actual_indent:
            self._move_indent(current_indent, actual_indent)

        self._current_line += self._pending_indent
        self._pending_indent = ""
        self._predicted_indent = actual_indent

    def _move_indent(self, current_indent: int, target_indent: int):
        if target_indent > current_indent:
            self._indent_forward(target_indent - current_indent)
        elif target_indent < current_indent:
            self._indent_backward(current_indent - target_indent)

    def _indent_forward(self, columns: int):
        while columns >= self.tab_width:
            self._type_tab(self.tab_width)
            columns -= self.tab_width

        for _ in range(columns):
            self._type_char(" ")

    def _indent_backward(self, columns: int):
        while columns >= self.tab_width:
            self._type_shift_tab(self.tab_width)
            columns -= self.tab_width

        if columns:
            self._type_shift_tab(columns)

    def _type_char(self, char: str, render: bool = True):
        self.terminal.type_char(char, render=render)
        if render:
            self._after_type()

    def _type_tab(self, tab_width: int):
        if hasattr(self.terminal, "type_tab"):
            self.terminal.type_tab(tab_width)
        else:
            for _ in range(tab_width):
                self.terminal.type_char(" ", render=False)
        self._after_type()

    def _type_shift_tab(self, tab_width: int):
        if hasattr(self.terminal, "type_shift_tab"):
            self.terminal.type_shift_tab(tab_width)
        else:
            for _ in range(tab_width):
                self.terminal.type_char("\b")
        self._after_type()

    def _after_type(self):
        if self.delay_func:
            delay = self.delay_func()
            if delay > 0:
                self.sleep_func(delay)

        if self.tick_func:
            self.tick_func()

    def _seed_context(self, text: str):
        for line in text.splitlines():
            self._finish_line(line)
        self._line_start = text.endswith("\n")

    def _finish_line(self, line: str):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            return False

        indent = self._indent_columns(line)
        delta = indent - self._last_significant_indent
        if 2 <= delta <= 8:
            self._indent_deltas[delta] += 1
            self.tab_width = self._indent_deltas.most_common(1)[0][0]

        self._last_significant_indent = indent
        self._last_significant_line = stripped
        return True

    def _predict_next_indent(self) -> int:
        if not self._last_significant_line:
            return 0

        line = self._last_significant_line.rstrip()
        if line.endswith("\\") or self._has_unclosed_bracket(line):
            return 0

        indent = self._last_significant_indent
        if line.endswith(":"):
            return indent + self.tab_width
        if _DEDENT_START_RE.match(line):
            return max(0, indent - self.tab_width)
        return indent

    def _indent_columns(self, line: str) -> int:
        columns = 0
        for char in line:
            if char == " ":
                columns += 1
            elif char == "\t":
                columns += self.tab_width
            else:
                break
        return columns

    def _upcoming_indent(self, text: str) -> Optional[int]:
        if text == "":
            return None

        columns = 0
        for char in text:
            if char == " ":
                columns += 1
            elif char == "\t":
                columns += self.tab_width
            elif char == "\n":
                return columns
            else:
                return columns
        return None

    @staticmethod
    def _has_unclosed_bracket(line: str) -> bool:
        opens = line.count("(") + line.count("[") + line.count("{")
        closes = line.count(")") + line.count("]") + line.count("}")
        return opens > closes
