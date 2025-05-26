# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib

def script_path_string(script_name:str):
    folder = pathlib.Path(__file__).parent.resolve()
    print(folder)
    return str(folder / f"./shell_scripts/{script_name}.sh")