#!/usr/bin/env python3
import kratix_sdk as ks
from pathlib import Path

BASE = Path(__file__).parent
ks.set_input_dir(BASE / "local" / "input")
ks.set_output_dir(BASE / "local" / "output")
ks.set_metadata_dir(BASE / "local" / "metadata")

from pipeline import main
main()
