# Contributing to AskDB

First off, thanks for taking the time to contribute!

## Development Setup

1. Make sure you have Docker, Python 3.12+, and Node 18+ installed.
2. Clone the repository.
3. Copy `.env.example` to `.env` in both `frontend/` and `backend/` directories.
4. Run `docker-compose up --build` to spin up the local development environment.

## Pull Request Process

1. Ensure any install or build dependencies are removed before the end of the layer when doing a build.
2. Update the README.md with details of changes to the interface, this includes new environment variables, exposed ports, useful file locations and container parameters.
3. Increase the version numbers in any examples files and the README.md to the new version that this Pull Request would represent.
4. You may merge the Pull Request in once you have the sign-off of two other developers.

## Code Style

- **Python**: We use `black` for formatting and `ruff` for linting. We enforce strict type hints using `mypy`.
- **TypeScript**: We use `eslint` and `prettier` for static analysis and formatting. Ensure strict type checking is enabled.
