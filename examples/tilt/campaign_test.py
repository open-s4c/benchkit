#!/usr/bin/env python3
# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Minimal example to run tilt locks.
"""


from tiltlib import TiltLib
from test_bench import SimpleMutexTestBench as TestBench

from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.utils.dir import caller_dir

campaign_dir = caller_dir()
tilt_locks_dir = campaign_dir / "locks"
bench_src_dir = campaign_dir / "bench"
vsync_dir = (tilt_locks_dir / "../deps/libvsync/").resolve()

NB_RUNS = 1
LOCKS = [
	# "clhlock", # TODO: fix Tilt implementation
	"hemlock",
	"mcslock",
	"reciplock",
	"ticketlock",
	"twalock",
]


def get_campaign_test(tiltlib) -> CampaignCartesianProduct:
	benchmark_name = "test_mutex"
	return CampaignCartesianProduct(
		name="tilt",
		benchmark=TestBench(
			src_dir=bench_src_dir,
			shared_libs=[tiltlib],
		),
		nb_runs=NB_RUNS,
		variables={
			"lock": LOCKS + ["taslock", "caslock", "vcaslock-nolse", "vcaslock-lse"],
		},
		constants={
			"benchmark_name": benchmark_name,
		},
		debug=False,
		gdb=False,
		enable_data_dir=True,
		continuing=False,
	)

def main() -> None:
	tiltlib = TiltLib(tilt_locks_dir=tilt_locks_dir)
	tiltlib.build()

	campaigns = [
		get_campaign_test(tiltlib),
	]

	suite = CampaignSuite(campaigns=campaigns)
	suite.print_durations()
	suite.run_suite()


if __name__ == "__main__":
	main()
