#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT

"""Run tmux campaign dashboard.

Usage:
    tmux.py \
[(-c <campaign-path> | --campaign=<campaign-path>)]  \
[(-s <session-name> | --session=<session-name>)]
    tmux.py (-h | --help)

Options:
    -h --help                       Prints this help message.
    -c FILE --campaign=FILE         Path to the campaign to prepare dashboard
                                    for. By default, the script tries to select
                                    the last campaign accessed in the current
                                    directory.
    -s SESSION --session=SESSION    Name to give to the newly created tmux
                                    session.
                                    [default: benchkit]
"""


import os
import os.path
import sys
from typing import Dict, List, Tuple

import docopt
import libtmux


def get_campaign_file_dates(target_dir: str) -> List[Tuple[str, float]]:
    """
    Get the list of campaign file scripts in the given target directory.

    Args:
        target_dir (str): path to the target directory where to find campaign scripts.

    Returns:
        List[Tuple[str, float]]: list of tuples t where t[0] is the campaign filename and t[1] is
        the last access time of the file.
    """
    result = [
        (c, os.path.getatime(c))
        for c in os.listdir(target_dir)
        if (c.startswith("campaign-") or c.startswith("campaign_")) and c.endswith(".py")
    ]
    return result


def get_most_recent_campaign_path(campaign_files_dates: List[Tuple[str, float]]) -> str:
    """
    From the list of tuples t where t[0] is the campaign filename and t[1] is the last access time
    of the file, get the campaign file name that was accessed the latest.

    Args:
        campaign_files_dates (List[Tuple[str, float]]):
            list of tuples t where t[0] is the campaign filename and t[1] is the last access time of
            the file.

    Returns:
        str: the campaign file name that was accessed the latest from the given list.
    """
    campaign_file = os.path.abspath(sorted(campaign_files_dates, key=lambda e: e[1])[-1][0])
    result = os.path.abspath(campaign_file)
    return result


def main(args: Dict[str, str]) -> None:
    """
    Main function of the script.

    Args:
        args (Dict[str, str]): docopt arguments.
    """
    campaign_file = args["--campaign"]
    session_name = args["--session"]
    if campaign_file is None:
        campaign_files_dates = get_campaign_file_dates(".")
        if len(campaign_files_dates) == 0:
            script_dir = os.path.abspath(os.path.dirname(__file__))
            campaign_files_dates = get_campaign_file_dates(script_dir)

            if len(campaign_files_dates) == 0:
                print(
                    (
                        "No campaign found in current directory. "
                        "Change into a campaign directory or provide a path to "
                        '"--campaign" argument.'
                    ),
                    file=sys.stderr,
                )
                sys.exit(1)
        campaign_file = get_most_recent_campaign_path(campaign_files_dates)

    campaign_path = os.path.abspath(campaign_file)
    campaign_dir, campaign_file = os.path.split(campaign_path)

    start_dir = campaign_dir

    server = libtmux.Server()

    if server.has_session(session_name):
        print(f'Session "{session_name}" already exists.')
        return

    session = server.new_session(
        session_name=session_name,
        start_directory=start_dir,
    )
    window = session.attached_window

    campaign_pane = window.attached_pane
    campaign_pane.send_keys(
        f"./runbench.sh {campaign_file} ",
        enter=False,
        suppress_history=False,
    )

    below_pane = window.split_window(
        vertical=True,
        percent=20,
        start_directory=start_dir,
    )
    below_pane.send_keys(
        "tail --retry --follow=name /tmp/benchkit.sh",
        enter=True,
        suppress_history=False,
    )

    right_pane = campaign_pane.split_window(
        vertical=False,
        percent=40,
        start_directory=start_dir,
    )
    right_pane.send_keys(
        "htop -d 0",
        enter=True,
        suppress_history=False,
    )

    results_pane = campaign_pane.split_window(
        vertical=True,
        start_directory=start_dir,
    )
    results_pane.send_keys(
        (
            'watch "ls -1rt results/*.csv '
            "| tail -n 1 "
            "| xargs cat "
            "| sed -e '/^#/d' "
            "| cut -d ';' -f 1-12 "
            "| column -t -s ';'"
            '| tail -n 20"'
        ),
        enter=True,
        suppress_history=False,
    )

    campaign_pane.select_pane()

    print(f'Session "{session_name}" created.')


if __name__ == "__main__":
    main(args=docopt.docopt(__doc__))
