Flake8 JIRA TODO Checker
========================

[![CircleCI](https://circleci.com/gh/SimonStJG/flake8-jira-todo-checker/tree/master.svg?style=shield)](https://circleci.com/gh/SimonStJG/flake8-jira-todo-checker/tree/master)
[![PyPI](https://img.shields.io/pypi/v/flake8-jira-todo-checker.svg?color=green)](https://pypi.python.org/pypi/flake8-jira-todo-checker)
[![PyPI](https://img.shields.io/pypi/l/flake8-jira-todo-checker.svg?color=green)](https://pypi.python.org/pypi/flake8-jira-todo-checker)
[![PyPI](https://img.shields.io/pypi/pyversions/flake8-jira-todo-checker.svg)](https://pypi.python.org/pypi/flake8-jira-todo-checker)
[![PyPI](https://img.shields.io/pypi/format/flake8-jira-todo-checker.svg)](https://pypi.python.org/pypi/flake8-jira-todo-checker)

Flake8 plugin to check that:

 1. Every `TODO`, `FIXME`, `QQ` etc comment has a JIRA ID next to it.  
 2. Every JIRA ID refers to a JIRA card which is not closed.

In other words, this is valid as long as the JIRA card ABC-123 is not closed:

```
def hacky_function():
    # TODO ABC-123 Stop reticulating splines
    ...
```

However this would raise the new flake8 error `JIR001`:

```
def hacky_function():
    # TODO Stop reticulating splines
    ...
```

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
[jira-python](https://jira.readthedocs.io/en/master/examples.html#authentication) library.

For cookie-based username/password authentication, use the following configuration parameters:

1.  `jira-cookie-username`
1.  `jira-cookie-password`

For HTTP Basic username/password authentication, use the following configuration parameters:

1.  `jira-http-basic-username`
1.  `jira-http-basic-password`

For OAuth authentication, use the following configuration parameters:

1.  `jira-oauth-access-token`
1.  `jira-oauth-access-token-secret`
1.  `jira-oauth-consumer-key`
1.  `jira-oauth-key-cert-file`

For kerberos authentication, set the `jira-kerberos` configuration parameter to True. 

## Alternatives

This project is heavily inspired by the [Softwire TODO checker](https://github.com/Softwire/todo-checker).

## Releasing

1. `poetry run bump2version minor`
1. `git push && git push --tags`
1. `tox -e pypi`

# TODO

Test and add instructions for JIRA cloud.