# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Tilt shared library for drop-in replacement of pthread_mutex_t type and associated functions
(*_lock, *_unlock, *_init, etc.).
"""

import pathlib
import re
from typing import List, Optional, Tuple

from benchkit.sharedlibs import (
    EnvironmentVariables,
    FromSourceSharedLib,
    LdPreloadLibraries,
    PackageDependency,
)
from benchkit.shell.shell import shell_out
from benchkit.utils.types import PathType


class TiltLib(FromSourceSharedLib):
    """
    Tilt shared library for drop-in replacement of pthread_mutex_t type and associated functions
    """

    class LibTiltNotFoundError(Exception):
        """Error raised when tilt library is not found."""

    def __init__(
        self,
        src_path: PathType,
        debug_mode: bool,
    ) -> None:
        super().__init__(src_path=src_path, debug_mode=debug_mode)

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies()

    def configure(self) -> None:
        super().configure()

    def clean(self) -> None:
        """
        Clean the library build.
        """
        raise NotImplementedError

    def build_single_lock(
        self,
        lock: str,
        atomics: str,
        use_lse: bool,
    ) -> None:
        """
        Build the library for the given lock.

        Args:
            lock (str):
                the name of the lock to build.
            atomics (str):
                what atomics the lock is supposed to used.
                Supported: a64 (for armv8), c11 (for std atomic), blt (for builtins).
            use_lse (bool):
                whether to use LSE instructions on Armv8.
                TODO: not supported for now.
        """
        raise NotImplementedError

    def get_compiler(self) -> str:
        """
        Return the compiler used to build the tilt library.

        Returns:
            str: the compiler used to build the tilt library.
        """
        cmake_logpath = self.build_dir / "CMakeFiles/CMakeOutput.log"
        with open(cmake_logpath, "r") as cmake_logfile:
            for line in cmake_logfile:
                match = re.match(r"Compiler: (.*)\n", line)
                if match is not None:
                    break
        compiler = match.groups()[0].strip()
        return compiler

    def get_exact_compiler(self) -> PathType:
        """
        Return the absolute path to the compiler used to build the tilt library.

        Returns:
            PathType: the absolute path to the compiler used to build the tilt library.
        """
        compiler = self.get_compiler()
        which_compiler = shell_out(f"which {compiler}").strip()
        exact_compiler = pathlib.Path(which_compiler).resolve()
        return exact_compiler

    def atomics_suffix(
        self,
        atomics: str,  # pylint: disable=unused-argument
    ) -> str:
        """
        What is the suffix for the "atomics" part of the tilt library name.

        Args:
            atomics (str): atomics used to build the tilt library.

        Returns:
            str: the suffix to add to the library name.
        """
        # Notice that this has been deprecated.
        return ""

    def check_path_for_lock(
        self,
        lock: str,
        use_lse: bool,  # pylint: disable=unused-argument
        atomics: str,
        lib_name: str,
    ) -> Optional[PathType]:
        """
        Check that the expected path to the tilt library exists for the given lock.

        Args:
            lock (str): the lock to check.
            use_lse (bool): whether LSE was enabled to build the lock (TODO not implemtend).
            atomics (str): what atomics were used to build the lock.
            lib_name (str): the name of the library.

        Raises:
            self.LibTiltNotFoundError: if the path to the lock cannot be reached.

        Returns:
            Optional[PathType]: the path to the tilt library.
        """
        if not lock:  # baseline
            return None

        atomics_suffix = self.atomics_suffix(atomics=atomics)
        lock_path = self.build_dir / f"{lib_name}-{lock}{atomics_suffix}.so"
        libtilt_path = lock_path.resolve()

        if not libtilt_path.is_file():
            raise self.LibTiltNotFoundError(f'Unknown path to libtilt: "{libtilt_path}"')
        return libtilt_path

    def preload(  # pylint: disable=arguments-differ
        self,
        lock: str,
        use_lse: bool,
        atomics: str,
        lib_name: str,
        **kwargs,
    ) -> Tuple[LdPreloadLibraries, EnvironmentVariables]:
        ld_preloads, other_env_vars = super().preload(
            lock=lock,
            use_lse=use_lse,
            atomics=atomics,
            **kwargs,
        )

        libtilt_path = self.check_path_for_lock(
            lock=lock,
            use_lse=use_lse,
            atomics=atomics,
            lib_name=lib_name,
        )
        if libtilt_path is not None:
            ld_preloads.append(libtilt_path)

        return ld_preloads, other_env_vars
