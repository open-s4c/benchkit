# This folder contains the files for testing the ast-shell implementation of benchkit

## Configure venv

There is a `configure.sh` script. If run from this directory it wil create a working venv that can be started using `. ./venv/bin/activate`

## Running the tests

Run `python -m unittest ast_shell -v` in this folder to run the current tests.
This takes about 1400 seconds for the current folder.
It will spam the terminal to make it not do this add `-b` to the command.

other_tests.py is a file containing some personal testing code and will be converted to proper test cases at a later date

## Todo

- Smaller unit tests for the internal structures
- Tests for the async ast-shell
- Try something that takes less time for the timeout tests as they would fail on slower systems aswell.