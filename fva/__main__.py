"""python -m fva [sources|fetch|analyze|report|all]

  sources  which cores the default update_all databases ship, and the commit each build came from
  fetch    check out each open-source build at that commit, plus MAME's drivers
  analyze  classify every statement and place each core's needle -> results/results.json
  report   results/results.json -> results/index.html and results/ja/index.html
  all      the four in order
"""
import sys

from . import fetch, report, run, sources

STEPS = {"sources": sources.build, "fetch": fetch.run, "analyze": run.run, "report": report.build_all}

if __name__ == "__main__":
    args = sys.argv[1:] or ["all"]
    if args[0] not in (*STEPS, "all"):
        sys.exit(__doc__)
    for name in (STEPS if args[0] == "all" else [args[0]]):
        print(f"== {name}")
        STEPS[name]()
