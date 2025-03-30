# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.platforms import get_current_platform
from benchkit.shell.commands import command_from_str


def main():
    platform = get_current_platform()

    py_cmd = "python3 --version"
    platform.comm.shell(command=py_cmd)

    command = command_from_str(command=py_cmd)
    print(command)
    print(command.to_list_str())
    print(command.to_str())
    print(command.run_with(comm_layer=platform.comm))

    resolved_command = command.resolve(comm_layer=platform.comm)
    print(resolved_command)
    print(resolved_command.to_list_str())
    print(resolved_command.to_str())
    print(resolved_command.run_with(comm_layer=platform.comm))


if __name__ == "__main__":
    main()
