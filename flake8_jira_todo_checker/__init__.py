__version__ = "0.1.0"

import logging
import re

logger = logging.getLogger(__name__)


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
            help=("Valid JIRA project IDs, e.g. ABC"),
        )

    @classmethod
    def parse_options(cls, options):
        cls.jira_project_ids = options.jira_project_ids
        cls.todo_pattern = _construct_todo_pattern(options.jira_project_ids)

    def run(self):
        for line_number, line in enumerate(self.lines, start=1):
            for match in self.todo_pattern.finditer(line):
                yield from self._process_match(line, line_number, match)

    def _process_match(self, line, line_number, match):
        logger.debug("Found match: %s on line %s", match.span(), line)
        start_of_match = match.span()[0]
        if self.jira_project_ids:
            jira_card_id = match.group(2)
            if jira_card_id:
                logger.debug("Found JIRA ID in match: %s", jira_card_id)
            else:
                logger.debug("No JIRA ID found")

                yield _format_error(line, line_number, start_of_match)
        else:
            logger.debug("No JIRA project IDs set")
            yield _format_error(line, line_number, start_of_match)


def _format_error(line, line_number, start_of_match):
    detail = line.rstrip()[start_of_match : start_of_match + 20]
    if len(line.rstrip()) > start_of_match + 20:
        detail += "..."
    return (
        line_number,
        start_of_match,
        f"JIR001 TODO with missing or invalid JIRA card: {detail}",
        type(Checker),
    )


def _construct_todo_pattern(jira_project_ids):
    todo_like = r"todo|fix|fixme|qq"
    if jira_project_ids:
        return re.compile(
            rf"""
                ({todo_like})
                (
                    [ ]                                            # Single Whitespace
                    ({"|".join(jira_project_ids)})                 # JIRA project ID
                    -
                    \d+                                            # JIRA card number
                )?
            """,
            re.VERBOSE | re.IGNORECASE,
        )
    else:
        return re.compile(rf"({todo_like})", re.VERBOSE | re.IGNORECASE)
