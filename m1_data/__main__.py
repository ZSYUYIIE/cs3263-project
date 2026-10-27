"""CLI: python -m m1_data {fetch|build|check|all}"""
import argparse
import sys


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m m1_data", description=__doc__)
    p.add_argument("command", choices=["fetch", "build", "check", "all"])
    args = p.parse_args(argv)

    if args.command in ("fetch", "all"):
        from .fetch import fetch
        fetch()
    if args.command in ("build", "all"):
        from .build import build
        build()
    if args.command in ("check", "build", "all"):
        from .check import check
        problems = check()
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
