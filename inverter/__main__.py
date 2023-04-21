"""
    Allow inverter to be executable
    through `python -m inverter`.
"""


from inverter.cli import cli_app


def main():
    cli_app.main()


if __name__ == '__main__':
    main()
