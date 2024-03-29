Flake8 JIRA TODO Checker
========================

[![CircleCI](https://circleci.com/gh/SimonStJG/flake8-jira-todo-checker/tree/main.svg?style=shield)](https://circleci.com/gh/SimonStJG/flake8-jira-todo-checker/tree/main)
[![PyPI](https://img.shields.io/pypi/v/flake8-jira-todo-checker.svg?color=green)](https://pypi.python.org/pypi/flake8-jira-todo-checker)
[![PyPI](https://img.shields.io/pypi/l/flake8-jira-todo-checker.svg?color=green)](https://pypi.python.org/pypi/flake8-jira-todo-checker)
[![PyPI](https://img.shields.io/pypi/pyversions/flake8-jira-todo-checker.svg)](https://pypi.python.org/pypi/flake8-jira-todo-checker)
[![PyPI](https://img.shields.io/pypi/format/flake8-jira-todo-checker.svg)](https://pypi.python.org/pypi/flake8-jira-todo-checker)

Flake8 plugin to check that:

 1. Every `TODO` comment has a JIRA ID next to it.  
 2. Every JIRA ID refers to a JIRA issue which is not closed.
 3. All "TODO" comments use the word "TODO" ("FIXME", "QQ", etc are not allowed).

In other words, this is valid as long as the JIRA issue ABC-123 is not closed:

```
def hacky_function():
    # TODO ABC-123 Stop reticulating splines
    ...
```

However, none of these comments would be valid:

```
def hacky_function():
    # TODO No JIRA issue is attached here
    # TODO ABC-9182 Not valid if this JIRA issue is resolved!
    # TODO FIXME You can't use this word to denote a TODO
    ...
```

You can choose to run this project without connectivity to JIRA, in which case it will only check that every TODO has
an issue attached from the correct project.

## Configuration

### jira-project-ids

A list of valid JIRA project IDs can be provided via the flag `--jira-project-ids` or via the key `jira-project-ids`
in a flake8 configuration file, e.g.

```
jira-project-ids = ABC,DEF
```

If no project IDs are provided then all TODOs will be rejected.

### todo-synonyms

A list of words which will be treated like TODO can be provided via the flags `--allowed-todo-synonyms` and 
`--disallowed-todo-synonyms` or via the key `allowed-todo-synonyms` and `disallowed-todo-synonyms` in a flake8 
configuration file.  

`disallowed-todo-synonyms` will raise an error whenever found in the codebase, and `allowed-todo-synonyms` will raise an 
error only if it's missing a JIRA card or that JIRA card is invalid.

Defaults to:
```
allowed-todo-synonyms = TODO
disallowed-todo-synonyms = FIXME,QQ
```

### jira-server

The URL of the JIRA server, if unset the status of JIRA cards won't be checked.


### disallowed-jira-statuses, disallowed-jira-resolutions, and disallow-all-jira-resolutions

If a TODO is attached to a JIRA issue whose status is in `disallowed-jira-statuses` then an error will be reported, 
ditto if the JIRA card has a resolution in `disallowed-jira-resolutions`.  If `disallow-all-jira-resolutions` is set to 
`True`, then report an error if issue has any resolution. 

Defaults to:
```
disallowed-jira-statuses = Done
disallow-all-jira-resolutions = True
```

### JIRA Authentication

We support the same authentication methods as the 
[jira-python](https://jira.readthedocs.io/examples.html#authentication) library.

For cookie-based username/password authentication, use the following configuration parameters:

1.  `jira-cookie-username`
1.  `jira-cookie-password`

For HTTP Basic username/password authentication, use the following configuration parameters:

1.  `jira-http-basic-username`
1.  `jira-http-basic-password`

For JIRA cloud set `jira-http-basic-username` to your email address and `jira-http-basic-password` to your 
[API token](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/).

For OAuth authentication, use the following configuration parameters:

1.  `jira-oauth-access-token`
1.  `jira-oauth-access-token-secret`
1.  `jira-oauth-consumer-key`
1.  `jira-oauth-key-cert-file`

For kerberos authentication, set the `jira-kerberos` configuration parameter to True.

# Alternatives

This project is heavily inspired by the [Softwire TODO checker](https://github.com/Softwire/todo-checker).

# Licence

GNU General Public License v3 or later (GPLv3+)

# Development Setup

1. Install [pyenv](https://github.com/pyenv/pyenv-installer)
2. Install [poetry](https://python-poetry.org/)
3. `poetry install`

# Releasing

1. `poetry run bump2version minor`
1. `git push && git push --tags`
1. `tox -e pypi`
