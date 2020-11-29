import argparse
import os
from tempfile import NamedTemporaryFile

import pytest
from flake8.checker import FileChecker
from flake8.main.application import Application

from flake8_jira_todo_checker import Checker


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


class _TestFileChecker(FileChecker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reports = []

    def report(self, error_code, line_number, column, text):
        self.reports.append((error_code, line_number, column, text))


@pytest.fixture(scope="session")
def default_flake8_options():
    app = Application()
    app.initialize([])
    return app.options


@pytest.fixture(scope="session")
def checker(default_flake8_options):
    def factory(code, jira_project_ids):
        Checker.parse_options(argparse.Namespace(jira_project_ids=jira_project_ids, todo_synonyms=["FIX", "TODO"]))

        with NamedTemporaryFile(mode="w", suffix=".py", encoding="utf8", delete=False) as f:
            f.write(_strip_indent(code))

        try:
            # This is all very silly, but I'm not sure the best way to hook into flake8
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


@pytest.mark.parametrize(
    "code,jira_project_ids,expected_errors",
    [
        pytest.param(
            """
            def main():
                # TODO!
                pass
            """,
            [],
            [(None, 2, 6, "JIR001 TODO with missing or invalid JIRA card: TODO!")],
            id="plain todo",
        ),
        pytest.param(
            """
            def main():
                # TODO ABC-123
                pass
            """,
            ["ABC"],
            [],
            id="valid project id",
        ),
        pytest.param(
            """
            def main():
                # TODO DEF-123
                pass
            """,
            ["ABC"],
            [(None, 2, 6, "JIR001 TODO with missing or invalid JIRA card: TODO DEF-123")],
            id="invalid project id",
        ),
        pytest.param(
            """
            def main():
                # TODO DEF-123  FIXME
                pass
            """,
            ["ABC"],
            [
                (None, 2, 6, "JIR001 TODO with missing or invalid JIRA card: TODO DEF-123  FIXME"),
                (None, 2, 20, "JIR001 TODO with missing or invalid JIRA card: FIXME"),
            ],
            id="multiple TODOs on one line",
        ),
        pytest.param(
            """
            def main():
                # TODO DEF-123
                # TODO DEF-456
                pass
            """,
            ["ABC"],
            [
                (None, 2, 6, "JIR001 TODO with missing or invalid JIRA card: TODO DEF-123"),
                (None, 3, 6, "JIR001 TODO with missing or invalid JIRA card: TODO DEF-456"),
            ],
            id="multiple TODOs on multiple lines",
        ),
        pytest.param(
            """
            def main():
                # todo DEF-123
                # Fix DEF-456
                pass
            """,
            ["ABC"],
            [
                (None, 2, 6, "JIR001 TODO with missing or invalid JIRA card: todo DEF-123"),
                (None, 3, 6, "JIR001 TODO with missing or invalid JIRA card: Fix DEF-456"),
            ],
            id="case insensitive",
        ),
    ],
)
def test(checker, code, jira_project_ids, expected_errors):
    assert checker(code, jira_project_ids) == expected_errors
