# CultiCore

A wep app for tracking the growth of your crops.

Think about it like this: you have some land with some
plants of some type in a delimited area; you give the
area a name you can remember, and you know how many
productive plants you have in there. Now you want to
know how much water you spend keeping the plants
alive and productive, or how much production you
get from the area. Maybe you expand or shrink the
cultivation plot. For all of these problems, you
could use pen and paper, but having a dashboard
with all the information you need at a glance is
better. For now you have to provide the data
manually every day or so, but it might be possible
to automate everything with the right devices, if you
can afford that.

## Technology stack

- Python
- Flask
- Bootstrap
- SQLite3

## Local setup

1. Make sure you are located at the project root
2. Create a virtual environment with `python3 -m venv .venv`.
3. Install the dependencies with `pip install -r requirements.txt.`
4. Initialize the database with `flask --app flaskr init-db`
5. Start the app with `flask --app flaskr run --debug`

## Tests

Run the test suite with `pytest`.

## Linters

Lint the codebase with `ruff --check`

## Formatters

Format the Python files with `black`

## Git hooks

The repository ships a pre-commit hook that lints and checks the formatting of
the staged Python files and runs the unit test suite before every commit.

Install it once per clone with:

```sh
bash scripts/install_hooks.sh
```

The hook is stored in `scripts/hooks/pre-commit` and is activated by pointing
`core.hooksPath` to that directory. Remove it with `git config --unset core.hooksPath`.

The linter and the formatter run against the content of the git index, so they
check the exact code that is about to be committed. Skip individual checks with
`SKIP=lint,format,tests git commit`, or bypass the hook altogether with
`git commit --no-verify`.

## License

MIT licensed, check [here](./LICENSE.md).
