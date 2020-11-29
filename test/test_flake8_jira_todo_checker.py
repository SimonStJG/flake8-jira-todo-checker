import argparse
import os
from tempfile import NamedTemporaryFile

import pytest
from flake8.checker import FileChecker
from flake8.main.application import Application

from flake8_jira_todo_checker import Checker


class _TestFileChecker(FileChecker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reports = []

    def report(self, error_code, line_number, column, text):
        self.reports.append((error_code, line_number, column, text))


def _strip_indent(s: str):
    lines = s.splitlines(keepends=True)
    indent = None
    for line in lines:
        if line.strip():
            line_indent = len(line) - len(line.lstrip())
            if indent is None:
                indent = line_indent
            else:
                indent = min(line_indent, indent)

    result_lines = []
    for line in lines:
        if line.strip():
            result_lines.append(line[indent:])

    return "".join(result_lines)


@pytest.fixture(scope="session")
def default_flake8_options():
    app = Application()
    app.initialize([])
    return app.options


@pytest.fixture(scope="session")
def checker(default_flake8_options):
    def factory(code, jira_project_ids):
        Checker.parse_options(argparse.Namespace(jira_project_ids=jira_project_ids))

        with NamedTemporaryFile(
            mode="w", suffix=".py", encoding="utf8", delete=False
        ) as f:
            f.write(_strip_indent(code))

        try:
            flake8 = _TestFileChecker(
                f.name,
                checks={
                    "ast_plugins": [
                        {
                            "parameters": {"tree": True, "lines": True},
                            "plugin": Checker,
                            "name": Checker.name,
                        }
                    ]
                },
                options=default_flake8_options,
            )
            flake8.run_ast_checks()
            return flake8.reports
        finally:
            os.unlink(f.name)

    return factory


def test_plain_todo(checker):
    code = """
        def main():
            # TODO!
            pass
    """
    assert checker(code, []) == [
        (None, 2, 6, "JIR001 TODO with missing or invalid JIRA card: TODO!")
    ]


def test_jira_ids(checker):
    code = """
        def main():
            # TODO ABC-123
            pass
    """
    assert checker(code, ["ABC"]) == []


def test_missing_ids(checker):
    code = """
        def main():
            # TODO DEF-123
            pass
    """
    assert checker(code, ["ABC"]) == [
        (None, 2, 6, "JIR001 TODO with missing or invalid JIRA card: TODO DEF-123")
    ]


def test_multiline(checker):
    code = """
        def main():
            # TODO DEF-123  FIXME
            pass
    """
    assert checker(code, ["ABC"]) == [
        (
            None,
            2,
            6,
            "JIR001 TODO with missing or invalid JIRA card: TODO DEF-123  FIXME",
        ),
        (None, 2, 20, "JIR001 TODO with missing or invalid JIRA card: FIXME"),
    ]
