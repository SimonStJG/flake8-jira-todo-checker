import contextlib
import io
import os
import sys
import tempfile

import flake8.main.application
import pytest

import flake8_jira_todo_checker


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


@contextlib.contextmanager
def as_temporary_file(text, suffix):
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, encoding="utf8", delete=False) as f:
            f.write(_strip_indent(text))
        yield f.name
    finally:
        os.unlink(f.name)


def run_flake8(config, code):
    with as_temporary_file(code, ".py") as code_file:
        with as_temporary_file(config, ".ini") as config_file:
            try:
                actual_stdout = sys.stdout
                actual_stderr = sys.stderr

                # One of the flake8 maintainers "suggests" using TextIOWrapper when monkeypatching sys.stdout
                # https://github.com/PyCQA/flake8/issues/1419
                new_stdout_buffer = io.BytesIO()
                sys.stdout = io.TextIOWrapper(new_stdout_buffer, write_through=True)

                new_stderr_buffer = io.BytesIO()
                sys.stderr = io.TextIOWrapper(new_stderr_buffer, write_through=True)

                app = flake8.main.application.Application()
                app.run(["--config", config_file, code_file])

                flake8_stdout = new_stdout_buffer.getvalue().decode("utf-8")
                flake8_stderr = new_stderr_buffer.getvalue().decode("utf-8")
            finally:
                sys.stdout.close()
                sys.stderr.close()
                sys.stdout = actual_stdout
                sys.stderr = actual_stderr

            if flake8_stderr:
                raise ValueError(f"Error while running flake8: {flake8_stderr}")

            if flake8_stdout:
                for line in flake8_stdout.splitlines():
                    yield line.split(":", maxsplit=1)[1]


@pytest.fixture
def mock_jira_client(mocker):
    mock_client = mocker.MagicMock()
    mock_client.get_issues.return_value = {}

    def mock_jira_client_from_options(*args, **kwargs):
        return mock_client

    mocker.patch(
        f"{flake8_jira_todo_checker.Checker.__module__}.jira_client_from_options", mock_jira_client_from_options
    )
    return mock_client


@pytest.mark.parametrize(
    "code,expected_errors",
    [
        pytest.param(
            """
            def main():
                # TODO!
                pass
            """,
            ["2:7: JIR001 TODO with missing or malformed JIRA card: TODO!"],
            id="plain todo",
        ),
        pytest.param(
            """
            def main():
                # TODO ABC-123
                pass
            """,
            [],
            id="valid project id",
        ),
        pytest.param(
            """
            def main():
                # TODO DEF-123
                pass
            """,
            ["2:7: JIR001 TODO with missing or malformed JIRA card: TODO DEF-123"],
            id="invalid project id",
        ),
        pytest.param(
            """
            def main():
                # TODO DEF-123  FIXME
                pass
            """,
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
            [],
            id="Banned word as subset of legitimate word",
        ),
    ],
)
def test_todo_recognition(code, expected_errors):
    config = """
        [flake8]
        allowed-todo-synonyms = TODO
        disallowed-todo-synonyms=FIX,FIXME,QQ
        jira-project-ids = ABC
    """
    assert set(run_flake8(config, code)) == set(expected_errors)


@pytest.mark.parametrize(
    "jira_client_output,expected_errors",
    [
        pytest.param(
            {},
            ["2:7: JIR002 TODO with invalid JIRA card: TODO ABC-123"],
            id="No such issue",
        ),
        pytest.param(
            {"ABC-123": ("In Progress", None)},
            [],
            id="Valid issue",
        ),
        pytest.param(
            {"ABC-123": ("Done", None)},
            ["2:7: JIR003 TODO with JIRA card in invalid state (Status=Done): TODO ABC-123"],
            id="Disallowed Status",
        ),
        pytest.param(
            {"ABC-123": (None, "Done")},
            ["2:7: JIR003 TODO with JIRA card in invalid state (Resolution=Done): TODO ABC-123"],
            id="Disallowed Resolution",
        ),
    ],
)
def test_jira_integration(mock_jira_client, jira_client_output, expected_errors):
    config = """
        [flake8]
        allowed-todo-synonyms = TODO
        disallowed-todo-synonyms=FIX,FIXME,QQ
        jira-project-ids = ABC
        jira-server=http://example.example/
        jira-cookie-username=test
        jira-cookie-password=test
    """
    code = """
        def main():
            # TODO ABC-123
            pass
    """
    mock_jira_client.get_issues.return_value = jira_client_output

    assert set(run_flake8(config, code)) == set(expected_errors)
