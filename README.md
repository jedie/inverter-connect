# inverter

[![tests](https://github.com/jedie/inverter-connect/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/jedie/inverter-connect/actions/workflows/tests.yml)
[![codecov](https://codecov.io/github/jedie/inverter-connect/branch/main/graph/badge.svg)](https://app.codecov.io/github/jedie/inverter-connect)
[![inverter-connect @ PyPi](https://img.shields.io/pypi/v/inverter-connect?label=inverter-connect%20%40%20PyPi)](https://pypi.org/project/inverter-connect/)
[![Python Versions](https://img.shields.io/pypi/pyversions/inverter-connect)](https://github.com/jedie/inverter-connect/blob/main/pyproject.toml)
[![License GPL-3.0-or-later](https://img.shields.io/pypi/l/inverter-connect)](https://github.com/jedie/inverter-connect/blob/main/LICENSE)

Get information from Deye Microinverter

The whole thing is just a learning exercise for now. We will see.


# quickstart

Currently just clone the project and just start the cli (that will create a virtualenv and installs every dependencies)

Note: Please enable https://www.piwheels.org/ if you are on a Raspberry Pi !

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
│ debug-settings              Display (anonymized) MQTT server username and password               │
│ print-at-commands           Print one or more AT command values from Inverter.                   │
│ print-values                Print all known register values from Inverter, e.g.:                 │
│ publish-loop                Publish current data via MQTT (endless loop)                         │
│ read-register               Read register(s) from the inverter                                   │
│ set-time                    Set current date time in the inverter device.                        │
│ store-settings              Store MQTT server settings.                                          │
│ test-mqtt-connection        Test connection to MQTT Server                                       │
│ version                     Print version and exit                                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
```
[comment]: <> (✂✂✂ auto generated main help end ✂✂✂)


# most important commands


## print-values

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

Example output of `print-values` call:

![print-values](https://raw.githubusercontent.com/jedie/jedie.github.io/master/screenshots/inverter-connect/2023-04-28_08-55.png "2023-04-28_08-55.png")

----


## print-at-commands

Help from `./cli.py print-at-commands --help` Looks like:

[comment]: <> (✂✂✂ auto generated print-at-commands help start ✂✂✂)
```
Usage: ./cli.py print-at-commands [OPTIONS] IP [COMMANDS]...

 Print one or more AT command values from Inverter.
 Use all known AT commands, if no one is given, e.g.:
 .../inverter-connect$ ./cli.py print-at-commands 192.168.123.456
 Or specify one or more AT-commands, e.g.:
 .../inverter-connect$ ./cli.py print-at-commands 192.168.123.456 WEBVER .../inverter-connect$
 ./cli.py print-at-commands 192.168.123.456 WEBVER WEBU
 e.g.: Set NTP server, enable NTP and check the values:
 .../inverter-connect$ ./cli.py print-at-commands 192.168.123.456 NTPSER=192.168.1.1 NTPEN=on
 NTPSER NTPEN
 wait a while and request the current date time:
 .../inverter-connect$ ./cli.py print-at-commands 192.168.123.456 NTPTM
 (Note: The prefix "AT+" will be added to every command)

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────╮
│ --port                INTEGER RANGE [1000<=x<=65535]  Port of the inverter                       │
│                                                       [default: 48899; 1000<=x<=65535]           │
│ --debug/--no-debug                                    [default: no-debug]                        │
│ --help                                                Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
```
[comment]: <> (✂✂✂ auto generated print-at-commands help end ✂✂✂)

Example output of `print-at-commands` call:

![print-at-commands](https://raw.githubusercontent.com/jedie/jedie.github.io/master/screenshots/inverter-connect/2023-04-28_08-57.png "2023-04-28_08-57.png")

----


## read-register

Help from `./cli.py read-register --help` Looks like:

[comment]: <> (✂✂✂ auto generated read-register help start ✂✂✂)
```
Usage: ./cli.py read-register [OPTIONS] IP REGISTER LENGTH

 Read register(s) from the inverter
 e.g.: read 3 registers starting from 0x16:
 .../inverter-connect$ ./cli.py read-register 192.168.123.456 0x16 3
 e.g.: read the first 32 registers:
 .../inverter-connect$ ./cli.py read-register 192.168.123.456 0 32
 The start address can be pass as decimal number or as hex string, e.g.: 0x123

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────╮
│ --port                INTEGER RANGE [1000<=x<=65535]  Port of the inverter                       │
│                                                       [default: 48899; 1000<=x<=65535]           │
│ --debug/--no-debug                                    [default: debug]                           │
│ --help                                                Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
```
[comment]: <> (✂✂✂ auto generated read-register help end ✂✂✂)

Example output of `read-register` call:

![read-register](https://raw.githubusercontent.com/jedie/jedie.github.io/master/screenshots/inverter-connect/2023-04-28_08-53.png "2023-04-28_08-53.png")

----


# start development

For development, we have a separate CLI, just call it:
```bash
~/inverter-connect$ ./dev-cli.py --help
```

The output of `./dev-cli.py --help` looks like:

[comment]: <> (✂✂✂ auto generated dev help start ✂✂✂)
```
Usage: ./dev-cli.py [OPTIONS] COMMAND [ARGS]...

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────╮
│ --help      Show this message and exit.                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────╮
│ check-code-style            Check code style by calling darker + flake8                          │
│ coverage                    Run and show coverage.                                               │
│ fix-code-style              Fix code style of all inverter source code files via darker          │
│ install                     Run pip-sync and install 'inverter' via pip as editable.             │
│ mypy                        Run Mypy (configured in pyproject.toml)                              │
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
[comment]: <> (✂✂✂ auto generated dev help end ✂✂✂)

----


# credits

Others before me have done good work. In particular, I have learned a lot from the following projects:

* https://github.com/s10l/deye-logger-at-cmd
* https://github.com/kbialek/deye-inverter-mqtt
* https://github.com/StephanJoubert/home_assistant_solarman

The included definitions yaml files are from:

https://github.com/StephanJoubert/home_assistant_solarman/tree/main/custom_components/solarman/inverter_definitions


# various links

* Discussion: https://www.photovoltaikforum.com/thread/201065-inverter-connect-daten-vom-deye-wechselrichter-per-python-abrufen/ (de)
