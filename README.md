Flake8 JIRA TODO Checker
========================

[![CircleCI](https://circleci.com/gh/SimonStJG/flake8-jira-todo-checker/tree/master.svg?style=shield)](https://circleci.com/gh/SimonStJG/flake8-jira-todo-checker/tree/master)
[![PyPI](https://img.shields.io/pypi/v/flake8-jira-todo-checker.svg?color=green)](https://pypi.python.org/pypi/flake8-jira-todo-checker)
[![PyPI](https://img.shields.io/pypi/l/flake8-jira-todo-checker.svg?color=green)](https://pypi.python.org/pypi/flake8-jira-todo-checker)
[![PyPI](https://img.shields.io/pypi/pyversions/flake8-jira-todo-checker.svg)](https://pypi.python.org/pypi/flake8-jira-todo-checker)
[![PyPI](https://img.shields.io/pypi/format/flake8-jira-todo-checker.svg)](https://pypi.python.org/pypi/flake8-jira-todo-checker)

Flake8 plugin to check that every `TODO`, `FIXME`, `QQ` etc comment has a JIRA ID next to it.

In other words, this is valid:

```
def hacky_function():
    # TODO ABC-123 Stop reticulating splines
    ...
```

But this would raise the new flake8 error `JIR001`:

```
def hacky_function():
    # TODO Stop reticulating splines
    ...
```

## Configuration

### jira-project-ids

A list of valid JIRA project IDs can be provided via the flag `--jira-project-ids` or via the key `jira-project-ids`
in a flake8 configuration file, e.g

```
jira-project-ids = ABC,DEF
```

If no project IDs are provided then all TODOs will be rejected.

### todo-synonyms

A list of words which will be treated like TODO can be provided via the flag `--todo-synonyms` or via the key 
`todo-synonyms` in a flake8 configuration file.  Defaults to:
```
todo-synonyms = TODO,FIX,QQ
```
