import os
import subprocess
from contextlib import contextmanager
from tempfile import NamedTemporaryFile

import pytest


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


@contextmanager
def as_temporary_file(text, suffix):
    try:
        with NamedTemporaryFile(mode="w", suffix=suffix, encoding="utf8", delete=False) as f:
            f.write(_strip_indent(text))
        yield f.name
    finally:
        os.unlink(f.name)


def run_flake8(config, code):
    with as_temporary_file(code, ".py") as code_file:
        with as_temporary_file(config, ".ini") as config_file:
            proc = subprocess.run(
                ["flake8", "--config", config_file, code_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stderr = proc.stderr.decode("utf8").strip()
            if stderr:
                raise ValueError(f"Error while running flake8: {stderr}")
            for line in proc.stdout.decode("utf8").splitlines():
                yield line.split(":", maxsplit=1)[1]


standard_config = """
[flake8]
allowed-todo-synonyms = TODO
disallowed-todo-synonyms=FIX,FIXME,QQ
jira-project-ids = ABC
"""


@pytest.mark.parametrize(
    "code,config,expected_errors",
    [
        pytest.param(
            """
            def main():
                # TODO!
                pass
            """,
            standard_config,
            ["2:7: JIR001 TODO with missing or malformed JIRA card: TODO!"],
            id="plain todo",
        ),
        pytest.param(
            """
            def main():
                # TODO ABC-123
                pass
            """,
            standard_config,
            [],
            id="valid project id",
        ),
        pytest.param(
            """
            def main():
                # TODO DEF-123
                pass
            """,
            standard_config,
            ["2:7: JIR001 TODO with missing or malformed JIRA card: TODO DEF-123"],
            id="invalid project id",
        ),
        pytest.param(
            """
            def main():
                # TODO DEF-123  FIXME
                pass
            """,
            standard_config,
            [
                "2:7: JIR001 TODO with missing or malformed JIRA card: TODO DEF-123  FIXME",
                "2:21: JIR004 Invalid word used instead of TODO: FIXME",
                "2:21: JIR001 TODO with missing or malformed JIRA card: FIXME",
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
            standard_config,
            [
                "2:7: JIR001 TODO with missing or malformed JIRA card: TODO DEF-123",
                "3:7: JIR001 TODO with missing or malformed JIRA card: TODO DEF-456",
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
            standard_config,
            [
                "2:7: JIR004 Invalid word used instead of TODO: todo DEF-123",
                "2:7: JIR001 TODO with missing or malformed JIRA card: todo DEF-123",
                "3:7: JIR004 Invalid word used instead of TODO: Fix DEF-456",
                "3:7: JIR001 TODO with missing or malformed JIRA card: Fix DEF-456",
            ],
            id="case insensitive",
        ),
        pytest.param(
            """
            def fixture():
                # Suffix and Fixture are suspicious words
                pass
            """,
            standard_config,
            [],
            id="Banned word as subset of legitimate word",
        ),
    ],
)
def test(code, config, expected_errors):
    assert list(run_flake8(config, code)) == expected_errors
