"""Run: python scripts/convert_to_parquet.py [--data-dir data] [--output-dir ...]."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.metrics.parquet_store import ensure_parquet

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    path, manifest = ensure_parquet(args.data_dir, args.output_dir)
    print(json.dumps({"directory": str(path), **manifest}, indent=2))
