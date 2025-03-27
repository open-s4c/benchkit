# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit CLI.

Usage:
  benchkit install [--editable | --repo=<repo_path>]
  benchkit activate
  benchkit init \
    [--module=<mod> | --command=<cmd> | --run-command=<rcmd> [--build-command=<bcmd>] ] \
    [--single-file | --full] [--git] [--current-dir=<dir>] [--nb-runs=<n>]
  benchkit run [--campaign-file=<file>]
  benchkit module list
  benchkit module run --module=<mod>
  benchkit module init --module=<mod>
  benchkit (-h | --help)
  benchkit --version

Options:
  -h --help                   Show this help message.
  --version                   Show version.
  --command=<cmd>             Command to execute.
  --build-command=<bcmd>      Command to build before running.
  --run-command=<rcmd>        Command to run after building.
  --current-dir=<dir>         Directory to run the command in [default: .].
  --nb-runs=<n>               Number of times to execute the command [default: 5].
  --single-file               Create a minimal single-file setup [default: True].
  --full                      Create a full benchmark structure [default: False].
  --module=<mod>              Specify a module [default: none].

Examples:
  benchkit init --command="echo myresult" --nb-runs=3
  benchkit init --single-file
  benchkit init --full
  benchkit run --command="echo myresult" --nb-runs=3
  benchkit run --build-command="gcc -o test test.c" --run-command="./test" --nb-runs=5
  benchkit module list
  benchkit module run --module="leveldb"
"""


from docopt import docopt


def list_modules():
    """List available benchmark modules."""
    modules = ["leveldb", "kyotocabinet"]
    print("Available modules:", ", ".join(modules))


def run_module(args):
    """Run a predefined module."""
    print(f"Running module: {args['--module']}")


def init_module(args):
    """Initialize a new module."""
    print(f"Initializing module: {args['--module']}")


def main() -> None:
    args = docopt(__doc__)

    use_module: bool = args["module"]
    module: str = args["--module"]
    command: str = args["--command"]
    run_command: str = args["--run-command"]
    build_command: str = args["--build-command"]
    current_dir: str = args["--current-dir"]
    nb_runs: int = int(args["--nb-runs"]) if args["--nb-runs"] else 3
    campaign_file: str = args["--campaign-file"]

    run_command = command or run_command or "echo 'Replace this command'"
    build_command = build_command or ""
    current_dir = current_dir
    nb_runs = nb_runs

    if args["install"]:
        from benchkit.cli.binstall import benchkit_install

        if args["--editable"]:
            benchkit_install(editable=True)
        elif "--repo" in args:
            benchkit_install(editable=True, benchkit_repo_path=args["--repo"])
        else:
            benchkit_install(editable=False)
        return

    if args["activate"]:
        from benchkit.cli.binstall import benchkit_activate

        benchkit_activate()

    if args["init"]:
        from benchkit.cli.init import benchkit_init

        split_benchmark_campaign = False
        if args["--single-file"]:
            split_benchmark_campaign = False
        if args["--full"]:
            split_benchmark_campaign = True

        git = False
        if args["--git"]:
            git = True

        benchkit_init(
            build_command=build_command,
            run_command=run_command,
            nb_runs=nb_runs,
            command_dir=current_dir,
            campaign_filename="",
            git=git,
            split_benchmark_campaign=split_benchmark_campaign,
        )
        return

    if args["run"]:
        from benchkit.cli.run import benchkit_run

        benchkit_run(campaign_file=campaign_file)

    if args["module"]:
        print(use_module)
        print(module)
        raise NotImplementedError("Will come in the future.")


if __name__ == "__main__":
    main()
