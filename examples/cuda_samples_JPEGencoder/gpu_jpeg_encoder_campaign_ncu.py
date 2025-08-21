
#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
import shutil
from typing import Any, Dict, List, Iterable

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignIterateVariables, CampaignSuite
from benchkit.commandwrappers.ncu import NcuWrap, CommandWrapper
from benchkit.platforms import Platform
from benchkit.utils.types import PathType
from benchkit.sharedlibs import SharedLib
from benchkit.utils.dir import get_curdir, parentdir
from benchkit.platforms import get_current_platform

# Variables
vars = [
    {'image': './build/images/img1.jpg',
     'outdir': './build/encode_output/',
     'quality': 20,
     'subsampling': 411,
     'huffman': 1},
    {'image': './build/images/img3.jpg',
     'outdir': './build/encode_output/',
     'quality': 80,
     'subsampling': 422,
     'huffman': 0},
    {'image': './build/images/img5.jpg',
     'outdir': './build/encode_output/',
     'quality': 50,
     'subsampling': 444,
     'huffman': 1},
    {'image': './build/images/img7.jpg',
     'outdir': './build/encode_output/',
     'quality': 100,
     'subsampling': 440,
     'huffman': 0},
]

class JPEGEncodeBench(Benchmark):
    def __init__(
        self,
        command_wrappers: Iterable[CommandWrapper] = (),
        command_attachments: Iterable[CommandAttachment] = (),
        shared_libs: Iterable[SharedLib] = (),
        pre_run_hooks: Iterable[PreRunHook] = (),
        post_run_hooks: Iterable[PostRunHook] = (),
        platform: Platform | None = None,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )

        script_path = get_curdir(__file__)
        bench_path = script_path / "src"
        build_path = script_path / "build"

        self._bench_src_path = bench_path
        self._build_dir = build_path

        if platform is not None:
            self.platform = platform

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    '''
    Because this is matrix multiplication the outer dims of the 2 matrices have to match
    As a result mb_width = ma_height
    '''
    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "image",
            "outdir",
            "quality",
            "subsampling",
            "huffman"
        ]

    @staticmethod
    def get_tilt_var_names():
        return []

    def build_bench(
        self,
        **kwargs,
    ) -> None:

        if self._build_dir.is_dir() and len(str(self._build_dir)) > 4:
            shutil.rmtree(str(self._build_dir))

        self.platform.comm.makedirs(path=self._build_dir, exist_ok=True)

        self.platform.comm.shell(
            command="cmake ../src",
            current_dir=self._build_dir,
            output_is_log=True,
        )

        self.platform.comm.shell(
            command="make",
            current_dir=self._build_dir,
        )

    def single_run(
        self,
        image,
        outdir,
        quality,
        subsampling,
        huffman,
        **kwargs,
    ) -> str:
        current_dir = self._build_dir
        environment = self._preload_env(**kwargs)

        run_command = [
            "./nvJPEG_encoder",
            f"-i {image}",
            f"-o {outdir}",
            f"-q {quality}",
            f"-s {subsampling}",
            f"-huf {huffman}"
        ]

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=current_dir,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=True,
        )

        return output

    @staticmethod
    def _parse_results(
        image: str,
        outdir: str,
        quality: int,
        subsampling: int,
        huffman: int,
        output: str
    ) -> Dict[str, Any]:
        output_lines = output.splitlines()
        num_channels = 0
        channel_sizes = []
        time = 0.0
        for line in output_lines:
            if line.startswith("Image is "):
                num_channels = int(line.split(' ')[2]) 
            elif line.startswith("Channel "):
                sizes = line.split(': ')[1].split(' x ')
                size_tup = (int(sizes[0]), int(sizes[1]))
                channel_sizes.append(size_tup)
            elif line.startswith("Total time spent on encoding: "):
                time = float(line.split(': ')[1])

        names=[
            "image",
            "outdir",
            "quality",
            "subsampling",
            "huffman",
            "num_channels",
            "time"
        ]
        values = [image,outdir,quality,subsampling,huffman,num_channels,time]
        for i in range(num_channels):
            names.append(f"channel {i}")
            values.append(channel_sizes[i])

        return dict(zip(names,values))


    def parse_output_to_results(
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        result_dict = {}


        image = str(run_variables["image"])
        outdir = str(run_variables["outdir"])
        quality = int(run_variables["quality"])
        subsampling = int(run_variables["subsampling"])
        huffman = int(run_variables["huffman"])
        result_dict = self._parse_results(
            image,
            outdir,
            quality,
            subsampling,
            huffman,
            command_output)

        return result_dict


def main():
    ncu_wrapper = NcuWrap(user_set="full")
    nb_runs = 1
    platform = get_current_platform()

    bench = JPEGEncodeBench(
        platform=platform,
        command_wrappers=[ncu_wrapper],
        post_run_hooks=[ncu_wrapper.post_run_hook_update_results]
    )

    campaign = CampaignIterateVariables(
        name="gpuJPEGencode",
        benchmark=bench,
        nb_runs=nb_runs,
        variables=vars,
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True
    )

    campaign_suite = CampaignSuite(campaigns=[campaign])
    campaign_suite.run_suite()

    # campaign_suite.generate_graph(
    #     plot_name="lineplot",
    #     x="quality",
    #     y="time"
    # )


if __name__ == "__main__":
    main()
