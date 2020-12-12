import enum
import logging
import re

from flake8_jira_todo_checker.jira_client import add_jira_client_options, jira_client_from_options
from flake8_jira_todo_checker.version import __version__

logger = logging.getLogger(__name__)

_MAX_ERROR_DETAIL_LENGTH = 60


@enum.unique
class ErrorCode(str, enum.Enum):
    JIR001 = "JIR001 TODO with missing or malformed JIRA card"
    JIR002 = "JIR002 TODO with invalid JIRA card"
    JIR003 = "JIR003 TODO with JIRA card in invalid state"
    JIR004 = "JIR004 Invalid word used instead of TODO"


class Checker:
    name = "flake8-jira-todo-checker"
    version = __version__

    def __init__(self, tree, lines):
        self.lines = lines

    @classmethod
    def add_options(cls, parser):
        parser.add_option(
            "--jira-project-ids",
            action="store",
            parse_from_config=True,
            comma_separated_list=True,
            help="Valid JIRA project IDs, e.g. ABC.  If none provided, then any TODOs will report an error.",
        )
        parser.add_option(
            "--allowed-todo-synonyms",
            action="store",
            parse_from_config=True,
            comma_separated_list=True,
            default=["TODO"],
            help="Allowed words which will be treated like a TODO.  Defaults to TODO.",
        )
        parser.add_option(
            "--disallowed-todo-synonyms",
            action="store",
            parse_from_config=True,
            comma_separated_list=True,
            default=["FIXME", "QQ"],
            help="Disallowed words which will be treated like a TODO.  Defaults to FIXME, QQ.",
        )
        parser.add_option(
            "--disallowed-jira-statuses",
            action="store",
            comma_separated_list=True,
            help="If any JIRA issue has this status then an error will be reported.  Defaults to Done.",
            default=["Done"],
        )
        parser.add_option(
            "--disallowed-jira-resolutions",
            action="store",
            comma_separated_list=True,
            help="If any JIRA issue has this resolution then an error will be reported.  Unset by default.  It is not "
            "valid to set this at the same time as disallow-all-jira-resolutions.",
            default=[],
        )
        parser.add_option(
            "--disallow-all-jira-resolutions",
            action="store_true",
            help="Raise an error if a JIRA issue has a resolution.  defaults to True.  It is not valid to set this at "
            "the same time as disallowed-jira-resolutions.",
            default=True,
        )
        add_jira_client_options(parser)

    @classmethod
    def parse_options(cls, options):
        jira_project_ids = options.jira_project_ids
        allowed_todo_synonyms = options.allowed_todo_synonyms
        disallowed_todo_synonyms = options.disallowed_todo_synonyms

        cls.allowed_todo_synonyms = set(allowed_todo_synonyms)
        cls.jira_project_ids = jira_project_ids
        cls.todo_pattern = _construct_todo_pattern(jira_project_ids, allowed_todo_synonyms, disallowed_todo_synonyms)

        if options.disallow_all_jira_resolutions and options.disallowed_jira_resolutions:
            raise ValueError("You cannot set both disallow_all_jira_resolutions and disallowed_jira_resolutions")

        cls.disallowed_jira_statuses = options.disallowed_jira_statuses
        cls.disallowed_jira_resolutions = options.disallowed_jira_resolutions
        cls.disallow_all_jira_resolutions = options.disallow_all_jira_resolutions

        cls.jira_client = jira_client_from_options(options)

    def run(self):
        for line_number, line in enumerate(self.lines, start=1):
            for match in self.todo_pattern.finditer(line):
                yield from self._process_match(line, line_number, match)

    def _process_match(self, line, line_number, match):
        logger.debug("Found match: %s on line %s", match.span(), line)
        start_of_match = match.span(1)[0]

        todo_word = match.group(1)
        if todo_word not in self.allowed_todo_synonyms:
            yield _format_error(ErrorCode.JIR004, line, line_number, start_of_match)

        if self.jira_project_ids:
            jira_card_id = match.group(2)
            if jira_card_id:
                jira_card_id = jira_card_id.strip()
                logger.debug("Found JIRA ID in match: %s", jira_card_id)
                if self.jira_client:
                    issue = self.jira_client.get_issue(jira_card_id)
                    yield from self._check_issue_against_jira(issue, line, line_number, start_of_match)
            else:
                logger.debug("No JIRA ID found")

                yield _format_error(ErrorCode.JIR001, line, line_number, start_of_match)
        else:
            logger.debug("No JIRA project IDs set")
            yield _format_error(ErrorCode.JIR001, line, line_number, start_of_match)

    def _check_issue_against_jira(self, issue, line, line_number, start_of_match):
        if not issue:
            logger.debug("No such issue")
            yield _format_error(ErrorCode.JIR002, line, line_number, start_of_match)
        else:
            status, resolution = issue
            logger.debug("Found issue with status: %s and resolution: %s", status, resolution)
            if status in self.disallowed_jira_statuses:
                logger.debug("JIRA status is disallowed")
                yield _format_error(ErrorCode.JIR003, line, line_number, start_of_match)
            elif resolution and (self.disallow_all_jira_resolutions or resolution in self.disallowed_jira_resolutions):
                logger.debug("JIRA resolution is disallowed")
                yield _format_error(ErrorCode.JIR003, line, line_number, start_of_match)


def _format_error(error_code, line, line_number, start_of_match):
    detail = line.rstrip()[start_of_match : start_of_match + _MAX_ERROR_DETAIL_LENGTH]
    if len(line.rstrip()) > start_of_match + _MAX_ERROR_DETAIL_LENGTH:
        detail += "..."
    return (
        line_number,
        start_of_match,
        f"{error_code.value}: {detail}",
        type(Checker),
    )


def _construct_todo_pattern(jira_project_ids, allowed_todo_synonyms, disallowed_todo_synonyms):
    if not allowed_todo_synonyms:
        raise ValueError("You must provide at least one value for allowed-todo-synonyms")

    todo_synonyms = [*allowed_todo_synonyms, *disallowed_todo_synonyms]
    todo_like = "|".join(todo_synonyms)
    if jira_project_ids:
        return re.compile(
            rf"""
                [^a-z]                              # Not a character
                                                    #   (We don't want to match words which end with a todo synonym)
                ({todo_like})
                (
                    [ ]                             # Single Whitespace
                    ({"|".join(jira_project_ids)})  # JIRA project ID
                    -
                    \d+                             # JIRA card number
                )?
                [^a-z]                              # Not a character
                                                    #   (We don't want to match words which start with a todo synonym)
            """,
            re.VERBOSE | re.IGNORECASE,
        )
    else:
        return re.compile(rf"({todo_like})", re.VERBOSE | re.IGNORECASE)
