import unittest

from programmer.code_typing import CodeTypingHelper


class FakeTerminal:
    def __init__(self):
        self.lines = [""]
        self.cursor_x = 0
        self.ops = []

    def type_char(self, char, render=True):
        self.ops.append(("char", char, render))
        if char == "\n":
            self.lines.append("")
            self.cursor_x = 0
        elif char == "\b":
            self._remove_columns(1)
        elif char == "\t":
            self.type_tab(4, render=render)
        else:
            self._insert_text(char)

    def type_tab(self, tab_width=4, render=True):
        self.ops.append(("tab", tab_width, render))
        self._insert_text(" " * tab_width)

    def type_shift_tab(self, tab_width=4, render=True):
        self.ops.append(("shift_tab", tab_width, render))
        self._remove_columns(tab_width)

    def rendered_text(self):
        return "\n".join(self.lines)

    def _insert_text(self, text):
        line = self.lines[-1]
        while len(line) < self.cursor_x:
            line += " "
        self.lines[-1] = line[:self.cursor_x] + text + line[self.cursor_x:]
        self.cursor_x += len(text)

    def _remove_columns(self, columns):
        line = self.lines[-1]
        start = max(0, self.cursor_x - columns)
        if line[:self.cursor_x].strip():
            return
        self.lines[-1] = line[:start] + line[self.cursor_x:]
        self.cursor_x = start


class CodeTypingHelperTest(unittest.TestCase):
    def test_disabled_mode_types_every_character(self):
        terminal = FakeTerminal()
        code = "if ready:\n    draw()\n"

        helper = CodeTypingHelper(terminal, enabled=False)
        helper.type_text(code)
        helper.finish()

        char_ops = [op for op in terminal.ops if op[0] == "char"]
        self.assertEqual(char_ops, [("char", char, True) for char in code])
        self.assertFalse(any(op[0] == "tab" for op in terminal.ops))
        self.assertEqual(terminal.rendered_text(), code.rstrip("\n") + "\n")

    def test_enabled_mode_preserves_code_and_uses_tab_jumps(self):
        terminal = FakeTerminal()
        code = "if ready:\n    draw()\nelse:\n    wait()\n"

        helper = CodeTypingHelper(terminal, enabled=True)
        helper.type_text(code)
        helper.finish()

        self.assertEqual(terminal.rendered_text(), code)
        self.assertTrue(any(op[0] == "tab" for op in terminal.ops))
        self.assertTrue(any(op[0] == "shift_tab" for op in terminal.ops))

    def test_predicted_indent_is_first_rendered_newline_position(self):
        terminal = FakeTerminal()
        helper = CodeTypingHelper(terminal, enabled=True)

        helper.type_text("if ready:\n    draw()\n")
        helper.finish()

        newline_index = terminal.ops.index(("char", "\n", False))
        self.assertEqual(terminal.ops[newline_index + 1], ("tab", 4, True))

    def test_token_split_indentation_is_preserved(self):
        terminal = FakeTerminal()
        helper = CodeTypingHelper(terminal, enabled=True)

        helper.type_text("if ready:\n  ")
        helper.type_text("  draw()\n")
        helper.finish()

        self.assertEqual(terminal.rendered_text(), "if ready:\n    draw()\n")

    def test_tab_width_is_derived_from_generated_code(self):
        terminal = FakeTerminal()
        helper = CodeTypingHelper(terminal, enabled=True)

        helper.type_text("if ready:\n  draw()\n  wait()\n")
        helper.finish()

        self.assertEqual(terminal.rendered_text(), "if ready:\n  draw()\n  wait()\n")
        self.assertIn(("tab", 2, True), terminal.ops)

    def test_visible_same_chunk_dedent_uses_actual_indent(self):
        terminal = FakeTerminal()
        helper = CodeTypingHelper(terminal, enabled=True)
        code = "if tiny:\n  if nested:\n    glow()\n  done()\n"

        helper.type_text(code)
        helper.finish()

        self.assertEqual(terminal.rendered_text(), code)
        char_positions = [
            index
            for index, op in enumerate(terminal.ops)
            if op[0] == "char"
        ]
        chars = "".join(terminal.ops[index][1] for index in char_positions)
        glow_newline = char_positions[chars.index("glow()\n") + len("glow()")]

        self.assertEqual(terminal.ops[glow_newline], ("char", "\n", False))
        self.assertEqual(terminal.ops[glow_newline + 1], ("tab", 2, True))
        self.assertEqual(terminal.ops[glow_newline + 2], ("char", "d", True))

    def test_comments_blank_lines_tabs_and_inner_spaces(self):
        terminal = FakeTerminal()
        helper = CodeTypingHelper(terminal, enabled=True)
        code = "if ready:\n\t# note\n\tvalue = 'a b'\n\nprint('done')\n"
        expected_render = "if ready:\n    # note\n    value = 'a b'\n\nprint('done')\n"

        helper.type_text(code)
        helper.finish()

        self.assertEqual(terminal.rendered_text(), expected_render)
        self.assertIn(("char", " ", True), terminal.ops)

    def test_blank_line_keeps_next_prediction_at_blank_indent(self):
        terminal = FakeTerminal()
        helper = CodeTypingHelper(terminal, enabled=True)

        helper.type_text("if ready:\n    value = 1\n\nprint(value)\n")
        helper.finish()

        tab_ops = [op for op in terminal.ops if op[0] == "tab"]
        shift_tab_ops = [op for op in terminal.ops if op[0] == "shift_tab"]
        self.assertEqual(tab_ops, [("tab", 4, True)])
        self.assertEqual(shift_tab_ops, [])
        self.assertEqual(
            terminal.rendered_text(),
            "if ready:\n    value = 1\n\nprint(value)\n",
        )


if __name__ == "__main__":
    unittest.main()
