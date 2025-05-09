#! /usr/bin/env python3
# ruff: noqa: S605

import argparse
import os
import shlex
import sys

PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))
PROJECT_NAME = "cinemahub_server"
LOCAL_ENV_FILE = f"{PROJECT_ROOT}/.envs/.local/.cinemahub"
LOCAL_ENV_TEMPLATE = (
    "# This file contains environment variables local to this setup.\n"
    "# You can also use it to overwrite environment variables only on your machine.\n\n"
)


def parse_args(arguments):  # noqa
    parser = argparse.ArgumentParser(
        prog="project.py",
        description="Helper script to simplify the docker workflow."
    )

    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser(
        "start", help="Start the Web Server containers Use `project.py -d start` to run them in the background."
    )
    run_parser.add_argument("-d", "--deamon-mode", help="Run the containers in the background", action="store_true")
    run_parser.add_argument("-b", "--build", help="Rebuild the image before running", action="store_true")
    run_parser.add_argument("--no-cache", help="Do not use Docker cache when building", action="store_true")

    subparsers.add_parser("stop", help="Stop the running container.")
    restart_parser = subparsers.add_parser("restart", help="Restart the running container.")
    restart_parser.add_argument("action", help="The service to restart", nargs=argparse.REMAINDER)
    logs_parser = subparsers.add_parser("logs", help="View logs of the project")
    logs_parser.add_argument("-f", "--follow-logs", help="Follow logs", action="store_true")

    subparsers.add_parser(
        "shell", help=(
            "Start an interactive shell to access the inside of the "
            "container. This only works if the server's container has "
            "already been started using `project.py start`."
        ),
    )

    subparsers.add_parser("populate", help="Populate Project with basic data.")

    django_parser = subparsers.add_parser("django", help="Run a manage.py command, e.g.: `./project.py django migrate`")
    django_parser.add_argument("action", help="The django manage.py command to execute", nargs=argparse.REMAINDER)

    exec_parser = subparsers.add_parser("exec", help="Run command in the container.")
    exec_parser.add_argument("action", help="The command to run", nargs=argparse.REMAINDER)

    setup_parser = subparsers.add_parser("setup", help="Setup the local development environment.")
    setup_parser.add_argument(
        "-f", "--force",
        help="Force setup, even if the local environment is already set up. This may result in a loss of data.",
        action="store_true"
    )
    subparsers.add_parser("mypy", help="Run mypy tool on project files.")

    args = parser.parse_args(arguments)

    if not args.command:
        parser.print_help()
        exit()

    return args


class Interpreter:
    @classmethod
    def interpret(cls, args: argparse.Namespace):
        command_name = args.command.replace("-", "_")

        if not hasattr(cls, command_name):
            raise NotImplementedError(f"The command `{args.command}` is not found.")

        getattr(cls, command_name)(args)

    @classmethod
    def setup(cls, args: argparse.Namespace | None = None):
        """Setup the local development environment"""

        if (args and args.force) or not os.path.isfile(LOCAL_ENV_FILE):
            print(f"Setting up {LOCAL_ENV_FILE} file...")
            with open(LOCAL_ENV_FILE, "w+") as f:
                f.write(LOCAL_ENV_TEMPLATE)

    @classmethod
    def start(cls, args: argparse.Namespace):
        if not os.path.isfile(LOCAL_ENV_FILE):
            cls.setup()

        if args.build:
            build_command = ["docker-compose", f"-p {shlex.quote(PROJECT_NAME)}", "-f local.yml", "build"]
            if args.no_cache:
                build_command.append("--no-cache")
            os.system(" ".join(build_command))

        up_command = ["docker-compose", f"-p {shlex.quote(PROJECT_NAME)}", "-f local.yml", "up"]
        if args.deamon_mode:
            up_command.append("-d")
        os.system(" ".join(up_command))

    @classmethod
    def stop(cls, args: argparse.Namespace):
        command = ["docker-compose", f"-p {shlex.quote(PROJECT_NAME)}", "-f local.yml", "down"]
        os.system(" ".join(command))

    @classmethod
    def restart(cls, args: argparse.Namespace):
        command = [
            "docker-compose", f"-p {shlex.quote(PROJECT_NAME)}", "-f local.yml", "restart", " ".join(args.action)
        ]
        os.system(" ".join(command))

    @classmethod
    def logs(cls, args: argparse.Namespace):
        command = ["docker-compose", f"-p {shlex.quote(PROJECT_NAME)}", "-f local.yml", "logs"]
        if args.follow_logs:
            command.append("-f")
        os.system(" ".join(command))

    @classmethod
    def shell(cls, args: argparse.Namespace):
        command = ["docker-compose", f"-p {shlex.quote(PROJECT_NAME)}", "-f local.yml", "exec", "cinemahub", "bash"]
        os.system(" ".join(command))

    @classmethod
    def exec(cls, args: argparse.Namespace):
        command = [
            "docker-compose", f"-p {shlex.quote(PROJECT_NAME)}", "-f local.yml", "exec", "cinemahub",
            " ".join(args.action),
        ]
        os.system(" ".join(command))

    @classmethod
    def django(cls, args: argparse.Namespace):
        project_tag = f"-p {shlex.quote(PROJECT_NAME)}"
        extra_args = sys.argv[2:]
        command = [
            "docker-compose",
            *project_tag.split(),
            "-f", "local.yml",
            "exec", "cinemahub",
            "python", "manage.py",
            *extra_args
        ]
        os.execvp(command[0], command)

    @classmethod
    def populate(cls, args: argparse.Namespace):
        base_command = ["docker-compose", f"-p {shlex.quote(PROJECT_NAME)}", "-f local.yml", "exec", "cinemahub"]

        load_database_data_command = [
            *base_command, "python manage.py loaddata fixtures/data.json"
        ]
        os.system(" ".join(load_database_data_command))

    @classmethod
    def mypy(cls, args: argparse.Namespace):
        command = [
            "docker-compose", f"-p {shlex.quote(PROJECT_NAME)}", "-f local.yml", "exec", "-w /app/core", "-T",
            "cinemahub", "mypy --explicit-package-bases . --config-file=mypy.ini"
        ]
        os.system(" ".join(command))


if __name__ == "__main__":
    arguments = parse_args(sys.argv[1:])
    Interpreter.interpret(arguments)
