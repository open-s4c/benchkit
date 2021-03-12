#!/bin/sh
set -e

copyright_line1="# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved."
copyright_line2="# SPDX-License-Identifier: MIT"

# Iterate over all .py files in the current directory and its subdirectories, excluding venv/
find . -type d -name "venv" -prune -o -type f -name "*.py" -print | while IFS= read -r file; do
    header=$(head -n 3 "$file")
    case "$header" in
        *"$copyright_line1"*|*"$copyright_line2"*)
            # Do nothing if match found
            ;;
        *)
            echo "$file does not have the copyright header" >&2
            ;;
    esac
done
