# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
VolanoMark benchmark implementation for benchkit.

This module implements the benchkit protocol for the VolanoMark chat server
benchmark. VolanoMark is a Java-based messaging benchmark that measures
server-side scalability and message throughput under increasing numbers
of concurrent chat clients.

The implementation covers:
- Fetching the VolanoMark self-extracting Java bootstrap
- Initializing the benchmark by unpacking bundled resources
- Running the VolanoMark workload with configurable rooms and users
- Parsing performance metrics from VolanoMark output

Example:
    >>> from pathlib import Path
    >>> bench = VolanoBench()
    # ------------------------------------------------------------------
    # Fetch: download and initialize VolanoMark
    # ------------------------------------------------------------------
    >>> fetch_ctx = FetchContext.from_args(
    ...     fetch_args={
    ...         "parent_dir": Path("/tmp/src"),
    ...     }
    ... )
    >>> fetch_result = bench.fetch(ctx=fetch_ctx, **fetch_ctx.fetch_args)
    # ------------------------------------------------------------------
    # Build: no-op (VolanoMark does not require compilation)
    # ------------------------------------------------------------------
    >>> build_ctx = BuildContext.from_fetch(
    ...     fetch_ctx=fetch_ctx,
    ...     fetch_result=fetch_result,
    ... )
    >>> build_result = bench.build(ctx=build_ctx)
    # ------------------------------------------------------------------
    # Run: execute the VolanoMark benchmark
    # ------------------------------------------------------------------
    >>> run_ctx = RunContext.from_build(
    ...     build_ctx=build_ctx,
    ...     build_result=build_result,
    ... )
    >>> run_result = bench.run(
    ...     ctx=run_ctx,
    ...     rooms=50,
    ...     users=20,
    ...     count=101,
    ... )
    # ------------------------------------------------------------------
    # Collect: parse performance metrics from VolanoMark output
    # ------------------------------------------------------------------
    >>> collect_ctx = CollectContext.from_run(
    ...     run_ctx=run_ctx,
    ...     run_result=run_result,
    ... )
    >>> record = bench.collect(
    ...     ctx=collect_ctx,
    ...     bench_name="volanomark",
    ... )
    >>> record["messages/second"]
    652666
"""


import re
from pathlib import Path

from benchkit.core.bktypes import RecordResult
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext
from benchkit.dependencies.packages import PackageDependency
from benchkit.utils.fetchtools import curl, sed_edit


class VolanoBench:
    """
    Benchmark implementation for Volano bench.

    This class implements all phases of the benchkit protocol:
    - fetch: curl the source from Volano benchmark
    - build: Skipped
    - run: Execute specified volano workload
    - collect: Parse performance metrics from output
    """

    def fetch(
        self,
        ctx: FetchContext,
        parent_dir: Path,
    ) -> FetchResult:
        """
        Fetch and initialize the VolanoMark benchmark.

        Downloads the VolanoMark self-extracting Java bootstrap, executes it to
        unpack the benchmark files, applies minimal configuration fixes, and
        ensures all required scripts are executable. If the benchmark directory
        already exists, the fetch step is skipped.

        Args:
            ctx: FetchContext providing platform and execution capabilities.
            parent_dir: Directory where the Volano benchmark will be initialized.

        Returns:
            FetchResult containing the path to the initialized Volano benchmark directory.
        """

        platform = ctx.platform
        comm = platform.comm
        volano_dir = parent_dir / "volano"

        if not comm.isdir(volano_dir):
            comm.makedirs(path=volano_dir, exist_ok=True)

            curl(
                ctx=ctx,
                url="https://www.volano.com/files/volano_benchmark_2_9_0.class",
                parent_dir=volano_dir,
                name="volano_benchmark_2_9_0.class",
            )

            # running the self-extracting bootstrap
            ctx.exec(argv=["java", "volano_benchmark_2_9_0", "-o", "."], cwd=volano_dir)

            # edit the config
            sed_edit(
                ctx=ctx,
                base_dir=volano_dir,
                edits=[
                    ("s/host=[^ ]*/host=localhost/", Path("startup.sh")),
                    (
                        "/# Quit if we cannot find the Java executable file./i java=$(which java)",
                        Path("startup.sh"),
                    ),
                ],
            )

            # add execution permissions
            ctx.exec(
                argv=[
                    "chmod",
                    "+x",
                    "startup.sh",
                    "netserver.sh",
                    "netclient.sh",
                    "loopserver.sh",
                    "loopclient.sh",
                ],
                cwd=volano_dir,
            )

        return FetchResult(src_dir=volano_dir)

    def build(
        self,
        ctx: BuildContext,
    ) -> BuildResult:
        """
        Prepare the Volano benchmark for execution.

        VolanoMark is a Java-based benchmark that does not require a compilation
        or build step. All required artifacts are provided by the fetch phase.
        This method therefore performs no build actions and simply forwards the
        fetched source directory as the build directory.

        Args:
            ctx: BuildContext providing platform, fetch results, and execution capabilities.

        Returns:
            BuildResult containing:
                - build_dir: Path to the directory containing the Volano benchmark artifacts
        """
        result = BuildResult(
            build_dir=ctx.fetch_result.src_dir,
        )
        return result

    def run(
        self,
        ctx: RunContext,
        start: int = 1,
        rooms: int = 50,
        users: int = 20,
        count: int = 101,
        pause: int = 0,
        host: str = "localhost",
    ) -> RunResult:
        """
        Execute the VolanoMark chat server benchmark.

        Runs the VolanoMark workload by launching the Java-based chat server and
        initiating a client load with the specified number of rooms and users.
        Each room is populated with a fixed number of users, which exchange a
        configurable number of messages. The benchmark reports total message
        throughput and execution time upon completion.

        Args:
            ctx: RunContext providing platform, build results, and execution capabilities.
            start: Starting room number (default: 1).
            rooms: Number of chat rooms to create (default: 50).
            users: Number of users per room (default: 20).
            count: Number of messages sent per user (default: 101).
            pause: Pause duration between messages in milliseconds (default: 0).
            host: Hostname or IP address of the chat server to connect to (default: "localhost").

        Returns:
            RunResult containing the execution output from the VolanoMark benchmark.

        Example:
            >>> run_result = bench.run(
            ...     ctx=run_ctx,
            ...     rooms=50,
            ...     users=20,
            ...     count=101,
            ... )
        """

        build_dir = ctx.build_result.build_dir
        run_command = [
            "java",
            "-cp",
            "lib/volano-chat-server.jar",
            "COM.volano.Mark",
            "-run",
            "-start",
            f"{start}",
            "-rooms",
            f"{rooms}",
            "-users",
            f"{users}",
            "-count",
            f"{count}",
            "-pause",
            f"{pause}",
            "-host",
            f"{host}",
        ]
        exec_out = ctx.exec(argv=run_command, cwd=build_dir, output_is_log=True)
        result = RunResult(outputs=[exec_out])
        return result

    def collect(self, ctx: CollectContext) -> RecordResult:
        """
        Parse performance metrics from VolanoMark output.

        Extracts metrics from the final VolanoMark summary block, which looks like:

            VolanoMark version = 2.9.0
            Messages sent      = 101000
            Messages received  = 1919000
            Total messages     = 2020000
            Elapsed time       = 3.095 seconds
            Average throughput = 652666 messages per second

        Args:
            ctx: CollectContext providing access to run results.
            bench_name: Unused for VolanoMark parsing; kept for compatibility.

        Returns:
            Dictionary containing parsed metrics:
                - version: VolanoMark version string (e.g., "2.9.0")
                - messages_sent: Number of messages sent
                - messages_received: Number of messages received
                - total_messages: Total number of messages
                - duration: Elapsed time in seconds
                - messages_per_second: Average throughput in messages per second

        Raises:
            ValueError: If the expected VolanoMark summary block cannot be found or parsed.

        Example output:
            {
                "version": "2.9.0",
                "messages_sent": 101000,
                "messages_received": 1919000,
                "total_messages": 2020000,
                "duration": 3.095,
                "messages_per_second": 652666.0,
            }
        """
        command_output = ctx.run_result.outputs[-1].stdout

        # Match the whole summary block (whitespace tolerant).
        m = re.search(
            r"VolanoMark\s+version\s*=\s*(?P<version>[0-9]+(?:\.[0-9]+)*)\s*\n"
            r"Messages\s+sent\s*=\s*(?P<sent>[0-9]+)\s*\n"
            r"Messages\s+received\s*=\s*(?P<received>[0-9]+)\s*\n"
            r"Total\s+messages\s*=\s*(?P<total>[0-9]+)\s*\n"
            r"Elapsed\s+time\s*=\s*(?P<seconds>[0-9]+(?:\.[0-9]+)?)\s+seconds\s*\n"
            r"Average\s+throughput\s*=\s*(?P<mps>[0-9]+(?:\.[0-9]+)?)\s+messages\s+per\s+second",
            command_output,
            flags=re.MULTILINE,
        )

        if not m:
            raise ValueError(
                "Incoherent output from volano (missing VolanoMark summary block), "
                f"please check output:\n{command_output}"
            )

        gd = m.groupdict()
        return {
            "version": gd["version"],
            "messages_sent": int(gd["sent"]),
            "messages_received": int(gd["received"]),
            "total_messages": int(gd["total"]),
            "duration": float(gd["seconds"]),
            "messages_per_second": float(gd["mps"]),
        }

    @staticmethod
    def dependencies() -> list[PackageDependency]:
        """
        List system package dependencies required to build and run Volano.

        Returns:
            List of PackageDependency objects for required system packages.
            These are Ubuntu/Debian package names; other distributions may have
            different package names.

        Dependencies include:
            - jdk21-openjdk: Java 21 Development Kit
        """
        return [
            PackageDependency("jdk21-openjdk"),
        ]
