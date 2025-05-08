# Cinema Hub

## Setup Project

Install Docker, Docker Compose and you are done!

### Use `project.py` script

- To run the project, simply execute this command: `./project.py start -d`
- To populate the initial data, you can use populate command: `./project.py populate`
- To get access to the project's shell, use this command: `./project.py shell`
- To run django commands like migrations, use this command: `./project.py django [django_command]`
- To run static type checks, use mypy command: `./project.py mypy`
- To stop the project, use stop command: `./project.py stop`

### PostgreSQL

This app comes with PostgreSQL as a docker container. Which means you don't need to do anything,
just run the docker containers (defined in `local.yml`) and everything will be setup for you automatically.

## Setup Development

### pre-commit

- Install Docker and Docker Compose
- Clone project to your system: `git clone https://github.com/Mahdikhaloei/CinemaHub.git`
- Open project in your favorite IDE or Text Editor
- Install [pre-commit](https://pre-commit.com/) on your system
- Install pre-commit hooks: `pre-commit install && pre-commit install --hook-type pre-push`
