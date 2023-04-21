# inverter

[![tests](https://github.com/jedie/inverter-connect/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/jedie/inverter-connect-connect/actions/workflows/tests.yml)
[![codecov](https://codecov.io/github/jedie/inverter-connect/branch/main/graph/badge.svg)](https://app.codecov.io/github/jedie/inverter-connect)
[![inverter-connect @ PyPi](https://img.shields.io/pypi/v/inverter-connect?label=inverter-connect%20%40%20PyPi)](https://pypi.org/project/inverter-connect/)
[![Python Versions](https://img.shields.io/pypi/pyversions/inverter-connect)](https://github.com/jedie/inverter-connect-connect/blob/main/pyproject.toml)
[![License GPL-3.0-or-later](https://img.shields.io/pypi/l/inverter-connect)](https://github.com/jedie/inverter-connect-connect/blob/main/LICENSE)

Get information from Deye Microinverter

The whole thing is just a learning exercise for now. We will see.

## screenshots

Example output of `print-values` call:

![print-values](https://raw.githubusercontent.com/jedie/jedie.github.io/master/screenshots/inverter-connect/2023-04-21_08-53.png "2023-04-21_08-53.png")

----

Example output of `print-at-commands` call:

![print-at-commands](https://raw.githubusercontent.com/jedie/jedie.github.io/master/screenshots/inverter-connect/2023-04-21_08-52.png "2023-04-21_08-52.png")

----


## quickstart

Currently just clone the project and just start the cli (that will create a virtualenv and installs every dependencies)

e.g.:
```bash
~$ git clone https://github.com/jedie/inverter-connect.git
~$ cd inverter-connect
~/inverter-connect$ ./cli.py --help
```

The output of `./cli.py --help` looks like:

[comment]: <> (✂✂✂ auto generated main help start ✂✂✂)
```
Usage: ./cli.py [OPTIONS] COMMAND [ARGS]...

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────╮
│ --help      Show this message and exit.                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────╮
│ check-code-style            Check code style by calling darker + flake8                          │
│ coverage                    Run and show coverage.                                               │
│ fix-code-style              Fix code style of all inverter source code files via darker          │
│ install                     Run pip-sync and install 'inverter' via pip as editable.             │
│ mypy                        Run Mypy (configured in pyproject.toml)                              │
│ print-at-commands           Print one or more AT command values from Inverter.                   │
│ print-values                Print all known register values from Inverter, e.g.:                 │
│ publish                     Build and upload this project to PyPi                                │
│ safety                      Run safety check against current requirements files                  │
│ test                        Run unittests                                                        │
│ tox                         Run tox                                                              │
│ update                      Update "requirements*.txt" dependencies files                        │
│ update-test-snapshot-files  Update all test snapshot files (by remove and recreate all snapshot  │
│                             files)                                                               │
│ version                     Print version and exit                                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
```
[comment]: <> (✂✂✂ auto generated main help end ✂✂✂)


### most important commands


#### print-values

Help from `./cli.py print-values --help` Looks like:

[comment]: <> (✂✂✂ auto generated print-values help start ✂✂✂)
```
Usage: ./cli.py print-values [OPTIONS] IP

 Print all known register values from Inverter, e.g.:
 .../inverter-connect$ ./cli.py print-values 192.168.123.456

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────╮
│ --port                INTEGER RANGE [1000<=x<=65535]  Port of the inverter                       │
│                                                       [default: 48899; 1000<=x<=65535]           │
│ --debug/--no-debug                                    [default: no-debug]                        │
│ --help                                                Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
```
[comment]: <> (✂✂✂ auto generated print-values help end ✂✂✂)


#### print-at-commands

Help from `./cli.py print-at-commands --help` Looks like:

[comment]: <> (✂✂✂ auto generated print-at-commands help start ✂✂✂)
```
Usage: ./cli.py print-at-commands [OPTIONS] IP [COMMANDS]...

 Print one or more AT command values from Inverter.
 Use all known AT commands, if no one is given, e.g.:
 .../inverter-connect$ ./cli.py print-at-commands 192.168.123.456
 Or speficy one or more AT-commands, e.g.:
 .../inverter-connect$ ./cli.py print-at-commands 192.168.123.456 WEBVER .../inverter-connect$
 ./cli.py print-at-commands 192.168.123.456 WEBVER WEBU
 (Note: The prefix "AT+" will be added to every command)

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────╮
│ --port                INTEGER RANGE [1000<=x<=65535]  Port of the inverter                       │
│                                                       [default: 48899; 1000<=x<=65535]           │
│ --debug/--no-debug                                    [default: no-debug]                        │
│ --help                                                Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
```
[comment]: <> (✂✂✂ auto generated print-at-commands help end ✂✂✂)


## credits

Others before me have done good work. In particular, I have learned a lot from the following projects:

* https://github.com/s10l/deye-logger-at-cmd
* https://github.com/kbialek/deye-inverter-mqtt
* https://github.com/StephanJoubert/home_assistant_solarman

The included definitions yaml files are from:

https://github.com/StephanJoubert/home_assistant_solarman/tree/main/custom_components/solarman/inverter_definitions


