from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .checks import config_check, cron_check, discover_home, profile_inventory_check
from .models import DoctorReport
from .path_utils import safe_home_label
from .reporting import to_json, to_markdown


def build_report(mode: str, hermes_home: Path) -> DoctorReport:
    checks = [discover_home(hermes_home)]
    if mode in {"quick", "full", "post-update"}:
        checks.extend([profile_inventory_check(hermes_home), config_check(hermes_home), cron_check(hermes_home)])
    return DoctorReport.build(mode=mode, hermes_home=safe_home_label(hermes_home), checks=checks)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hermes-system-doctor")
    p.add_argument("command", choices=["discover", "quick", "full", "post-update", "version"])
    p.add_argument("--hermes-home", default="~/.hermes")
    p.add_argument(
        "--all-profiles",
        action="store_true",
        help="Scan all profiles under the selected Hermes home; currently the default when profiles/ exists.",
    )
    p.add_argument("--json", action="store_true")
    p.add_argument("--markdown", action="store_true")
    p.add_argument("--output")
    p.add_argument("--fail-on", choices=["unknown", "warn", "fail", "needs-approval"], default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "version":
        print(__version__)
        return 0
    report = build_report(args.command, Path(args.hermes_home).expanduser())
    rendered = to_json(report) if args.json else to_markdown(report)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.fail_on == "unknown" and report.status in {"UNKNOWN", "WARN", "FAIL", "NEEDS_APPROVAL"}:
        return 1
    if args.fail_on == "warn" and report.status in {"WARN", "FAIL", "NEEDS_APPROVAL"}:
        return 1
    if args.fail_on == "fail" and report.status in {"FAIL", "NEEDS_APPROVAL"}:
        return 2
    if args.fail_on == "needs-approval" and report.status == "NEEDS_APPROVAL":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
