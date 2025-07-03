# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from __future__ import annotations  # Otherwise Queue comlains about typing

import itertools
from multiprocessing import Queue
from subprocess import CalledProcessError, Popen, TimeoutExpired
from threading import Thread
from typing import Iterable, Optional, Tuple

from benchkit.shell.command_execution.io.output import Output


class CommandProcess:
    """Encaptulation of the Popen process with functions to use it in an asyncronous way"""
    def __init__(
        self,
        popen_object: Popen[bytes],
        output: Output,
        timeout: Optional[int],
        success_code: int = 0,
        ignore_exit_codes: Optional[Iterable[int]] = None,
    ):

        self.__popen_object: Popen[bytes] = popen_object
        self.__output: Output = output
        self.__timeout: Optional[int] = timeout
        self.__retcode_queue: Queue[Tuple[int, Optional[Exception]]] = Queue()
        self.success_code: int = success_code
        self.ignore_exit_codes: Iterable[int] = (
            (success_code,) if ignore_exit_codes is None else ignore_exit_codes
        )

        # add the success_code to the return codes to ignore
        if self.success_code not in self.ignore_exit_codes:
            self.ignore_exit_codes = itertools.chain([success_code], self.ignore_exit_codes)

        self.retcode: Optional[int] = None
        self.error: Optional[Exception] = None
        self.process: Thread = self.__wait_async()

    @staticmethod
    def __wait_func(
        subprocess: Popen[bytes],
        queue: Queue[Tuple[int, Optional[Exception]]],
        timeout: Optional[int],
        ignore_exit_codes: Iterable[int],
    ) -> None:
        try:
            retcode = subprocess.wait(timeout)
            if retcode not in ignore_exit_codes:
                queue.put(
                    (
                        retcode,
                        CalledProcessError(
                            retcode,
                            subprocess.args,
                        ),
                    )
                )
            else:
                queue.put((retcode, None))

        except TimeoutExpired as exc:
            # TODO: we can add some form of logging here to warn the user if something went wrong
            subprocess.terminate()
            subprocess.wait(1)
            queue.put((-1, exc))

    def __wait_async(self) -> Thread:
        waiting_thread = Thread(
            target=self.__wait_func,
            args=(
                self.__popen_object,
                self.__retcode_queue,
                self.__timeout,
                self.ignore_exit_codes,
            ),
        )
        waiting_thread.start()
        return waiting_thread

    def get_output(self) -> Output:
        """get the Output object related to this process
           can be used as input for other processes"""
        return self.__output

    def get_return_code(self) -> int:
        """halt until the process has a return code
           if the return code is not ignored
           or the waittime was exceded throw an error instead"""
        if self.error is not None:
            raise self.error
        if self.retcode:
            return self.retcode
        self.process.join()
        self.retcode, self.error = self.__retcode_queue.get()
        if self.error is not None:
            raise self.error
        return self.retcode

    # TODO: check how this interacts with ssh
    # THIS DOES NOT SEND IT TO THE RIGHT ONE -> move abstraction higher
    def signal(self, signalcode: int) -> None:
        self.__popen_object.send_signal(signalcode)
        self.__popen_object.wait(1)
