#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

from django.core.management import execute_from_command_line

COVERAGE_ACCEPTANCE = 20
FAIL_COLOR = "\033[91m"
RESET_COLOR = "\x1b[0m"


class CommandManager:
    """Custom manager for adding custom commands."""

    def __init__(self, *args, **kwargs) -> None:
        self.argv = kwargs.get("argv", [])
        self.command = self.get_command(self.argv)
        self.command_args = self.get_command_args(self.argv)
        self.default_settings = "config.settings.local"

    @staticmethod
    def get_command(args) -> str:
        """Get main command from args."""
        try:
            return args[1]
        except IndexError:
            return "help"

    @staticmethod
    def get_command_args(args) -> list:
        """Get command args."""
        try:
            return args[2:]
        except IndexError:
            return []

    def run_coverage(self) -> None:
        """Run test coverage."""
        self.default_settings = "config.settings.local"
        base_dir = Path(__file__).resolve(strict=True).parent
        os.environ.setdefault("COVERAGE_RCFILE", os.path.join(base_dir, ".coveragerc"))
        from coverage import Coverage
        cov = Coverage()
        cov.erase()
        cov.start()
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", self.default_settings)
        execute_from_command_line(self.argv)
        cov.stop()
        cov.save()
        cov.combine()
        if (cov_result := round(cov.report())) < COVERAGE_ACCEPTANCE:
            sys.exit(
                f"{FAIL_COLOR}ERROR! Your test coverage ({cov_result}%) is below "
                f"the acceptance coverage ({COVERAGE_ACCEPTANCE}%). {RESET_COLOR}"
            )
        cov.erase()

    def main(self) -> None:
        """Main method for invoking commands functionality."""
        if self.command == "test":
            self.run_coverage()
        else:
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", self.default_settings)
            execute_from_command_line(self.argv)


def main():
    """Run administrative tasks."""
    argv = sys.argv
    manager = CommandManager(argv=argv)
    manager.main()


if __name__ == "__main__":
    main()
