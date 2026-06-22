#!/usr/bin/env python
"""[HAND-WRITTEN] Django 관리 진입점. src/ 를 path 에 올린다."""

import os
import sys
from pathlib import Path


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
