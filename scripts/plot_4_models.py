#!/usr/bin/env python3
"""Rebuild the four-controller report and chart from saved CSV files."""

import sys

from compare_4_models import main


if __name__ == "__main__":
    main(["--plot-only", *sys.argv[1:]])
