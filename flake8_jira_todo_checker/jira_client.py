import logging
import pathlib
import textwrap

import jira

logger = logging.getLogger(__name__)

_MAX_ISSUES_PER_JIRA_QUERY = 100
_RECOGNISABLE_COMMENT_SUFFIX = "\n\n~This comment was automatically generated by the flake8-jira-todo-checker~"


class JiraClient:
    def __init__(self, jira_client):
        self._jira_client = jira_client

    def get_issues(self, issue_ids):
        if len(issue_ids) > _MAX_ISSUES_PER_JIRA_QUERY:
            raise ValueError("Unable to query for more than 100 issues")

        return {
            issue.key: issue
            # weirdly, this query will fail unless we pass the keys as lowercase
            # https://community.atlassian.com/t5/Jira-questions/JQL-search-by-issueId-fails-if-issue-key-LIST-has-a-deleted/qaq-p/99570
            for issue in self._jira_client.search_issues(
                f'issuekey in ({",".join(issue.lower() for issue in issue_ids)})', maxResults=_MAX_ISSUES_PER_JIRA_QUERY
            )
        }

    def fix_comment(self, issue, message, dry_run):
        if message:
            # \\ Is line break on JIRA
            expected_comment = f"{message}\n\\\\{_RECOGNISABLE_COMMENT_SUFFIX}"
        else:
            expected_comment = None

        comments = self._jira_client.comments(issue)

        existing_comment = None
        for comment in comments:
            if comment.body.endswith(_RECOGNISABLE_COMMENT_SUFFIX):
                existing_comment = comment
                break

        logger.debug("Existing comment: %s", existing_comment)

        if not expected_comment:
            if existing_comment:
                logger.debug("Deleting comment, no longer required")
                if dry_run:
                    print(f"Would delete comment on {issue}\n" + textwrap.indent(existing_comment.body, "\t") + "\n\n")
                else:
                    existing_comment.delete()
                return

            logger.debug("Found no comment and wasn't expecting one")
            return

        if not existing_comment:
            logger.debug("Adding new comment")
            if dry_run:
                print(f"Would add comment on {issue}\n" + textwrap.indent(expected_comment, "\t") + "\n\n")
            else:
                self._jira_client.add_comment(issue, expected_comment)
            return

        if expected_comment == existing_comment.body:
            logger.debug("Comments already match")
            return

        logger.debug("Updating existing comment")
        if dry_run:
            print(
                f"Would update comment on {issue} from \n"
                + textwrap.indent(existing_comment.body, "\t")
                + "\nto\n"
                + textwrap.indent(expected_comment, "\t")
                + "\n\n"
            )
        else:
            existing_comment.update(body=expected_comment)


def status_and_resolution(issue):
    status = issue.fields.status.name
    if issue.fields.resolution:
        resolution = issue.fields.resolution.name
    else:
        resolution = None
    return status, resolution


def add_jira_client_options(parser):
    parser.add_option(
        "--jira-server", action="store", parse_from_config=True, help="JIRA Server URL, e.g. http://localhost:8080"
    )

    parser.add_option(
        "--jira-cookie-username",
        action="store",
        parse_from_config=True,
        help="JIRA Cookie-based auth: Username",
        default=None,
    )
    parser.add_option(
        "--jira-cookie-password",
        action="store",
        parse_from_config=True,
        help="JIRA Cookie-based auth: Password",
        default=None,
    )
    parser.add_option(
        "--jira-http-basic-username",
        action="store",
        parse_from_config=True,
        help="JIRA HTTP Basic Auth: Username",
        default=None,
    )
    parser.add_option(
        "--jira-http-basic-password",
        action="store",
        parse_from_config=True,
        help="JIRA HTTP Basic Auth: Password",
        default=None,
    )
    parser.add_option(
        "--jira-oauth-access-token", action="store", parse_from_config=True, help="JIRA OAuth: Access Token"
    )
    parser.add_option(
        "--jira-oauth-access-token-secret",
        action="store",
        parse_from_config=True,
        help="JIRA OAuth: Access Token Secret",
    )
    parser.add_option(
        "--jira-oauth-consumer-key", action="store", parse_from_config=True, help="JIRA OAuth: Consumer Key"
    )
    parser.add_option(
        "--jira-oauth-key-cert-file", action="store", parse_from_config=True, help="JIRA OAuth: Key Cert File"
    )
    parser.add_option("--jira-kerberos", action="store_true", parse_from_config=True, help="JIRA Kerberos Auth")


def jira_client_from_options(options):
    kwargs = {}

    jira_server = options.jira_server

    if not jira_server:
        logger.debug("Not using JIRA client")
        return None

    kwargs["server"] = jira_server

    jira_cookie_username = options.jira_cookie_username
    jira_cookie_password = options.jira_cookie_password
    jira_http_basic_username = options.jira_http_basic_username
    jira_http_basic_password = options.jira_http_basic_password
    jira_oauth_access_token = options.jira_oauth_access_token
    jira_oauth_access_token_secret = options.jira_oauth_access_token_secret
    jira_oauth_consumer_key = options.jira_oauth_consumer_key
    jira_oauth_key_cert_file = options.jira_oauth_key_cert_file
    jira_kerberos = options.jira_kerberos

    is_cookie_auth = any([jira_cookie_username, jira_cookie_password])
    is_basic_auth = any([jira_http_basic_username, jira_http_basic_password])
    is_oauth = any(
        [jira_oauth_access_token, jira_oauth_access_token_secret, jira_oauth_consumer_key, jira_oauth_key_cert_file]
    )
    is_kerberos = jira_kerberos

    auth_methods_requested = {
        "Cookie Auth": is_cookie_auth,
        "Basic Auth": is_basic_auth,
        "OAuth": is_oauth,
        "Kerberos": is_kerberos,
    }

    num_auth_methods_requested = sum(auth_methods_requested.values())
    if num_auth_methods_requested == 0:
        raise ValueError("No JIRA authentication details provided")
    elif num_auth_methods_requested > 1:
        names_of_auth_methods_requested = [name for name, was_requested in auth_methods_requested if was_requested]
        raise ValueError(
            f"Too many JIRA authentication methods requested: {', '.join(names_of_auth_methods_requested)}"
        )
    elif is_cookie_auth:
        kwargs["auth"] = (jira_cookie_username, jira_cookie_password)
    elif is_basic_auth:
        kwargs["basic_auth"] = (jira_http_basic_username, jira_http_basic_password)
    elif is_oauth:
        kwargs["oauth"] = {
            "access_token": jira_oauth_access_token,
            "access_token_secret": jira_oauth_access_token_secret,
            "consumer_key": jira_oauth_consumer_key,
            "key_cert": pathlib.Path(jira_oauth_key_cert_file).read_text(),
        }
    elif is_kerberos:
        kwargs["kerberos"] = True
    else:
        raise RuntimeError("Programmer error - unhandled case")

    return JiraClient(jira.JIRA(**kwargs))
