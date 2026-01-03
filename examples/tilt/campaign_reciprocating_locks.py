#!/usr/bin/env python3
# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Campaign to run the Reciprocating locks benchmarks using Tilt.
"""


from tiltlib import TiltLib
from mutex_bench import MutexBench

from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.utils.dir import caller_dir

campaign_dir = caller_dir()
tilt_locks_dir = campaign_dir / "locks"
bench_src_dir = campaign_dir / "bench"
vsync_dir = (tilt_locks_dir / "../deps/libvsync/").resolve()

NB_RUNS = 7
LOCKS = [
	# "clhlock", # TODO: fix Tilt implementation
	"hemlock",
	"mcslock",
	"reciplock",
	"ticketlock",
	"twalock",
]

BENCHMARK_DURATION_SECONDS = 10


def get_campaign_mutex(tiltlib, benchmark_name: str) -> CampaignCartesianProduct:
	return CampaignCartesianProduct(
		name="tilt",
		benchmark=MutexBench(
			src_dir=bench_src_dir,
			shared_libs=[tiltlib],
		),
		nb_runs=NB_RUNS,
		variables={
			"lock": LOCKS,
			"nb_threads": range(1, 17), # 1-16 threads
		},
		constants={
			"benchmark_name": benchmark_name,
			"benchmark_duration_seconds": BENCHMARK_DURATION_SECONDS,
		},
		debug=False,
		gdb=False,
		enable_data_dir=True,
		continuing=False,
		benchmark_duration_seconds=BENCHMARK_DURATION_SECONDS,
		pretty={
			"lock": {
				# "clhlock": "CLH lock",
				"hemlock": "Hemlock",
				"mcslock": "MCS lock",
				"reciplock": "Reciprocating lock",
				"ticketlock": "Ticketlock",
				"twalock": "TWA lock",
			},
		},
	)

def main() -> None:
	tiltlib = TiltLib(tilt_locks_dir=tilt_locks_dir)
	tiltlib.build()

	campaigns = [
		get_campaign_mutex(tiltlib, "bench_mutex"), # High contention
		get_campaign_mutex(tiltlib, "bench_mutex_moderate"), # Moderate contention
	]

	suite = CampaignSuite(campaigns=campaigns)
	suite.print_durations()
	suite.run_suite()

	suite.generate_graph(
		plot_name="lineplot",
		x="nb_threads",
		y="total_iterations",
		hue="lock",
	)


if __name__ == "__main__":
	main()
