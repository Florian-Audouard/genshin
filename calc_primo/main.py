from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable


DATE_FMT = "%d/%m/%Y"  # dd/mm/yyyy


def parse_date_ddmmyyyy(value: str) -> date:
    try:
        return datetime.strptime(value, DATE_FMT).date()
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Expected format dd/mm/yyyy (e.g. 08/04/2026)."
        ) from e


def format_date_ddmmyyyy(d: date) -> str:
    return d.strftime(DATE_FMT)


@dataclass(frozen=True)
class Version:
    major: int
    minor: int

    @classmethod
    def parse(cls, s: str) -> "Version":
        parts = s.strip().split(".")
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            raise argparse.ArgumentTypeError(
                f"Invalid patch version '{s}'. Expected like 6.5 or 7.0."
            )
        return cls(int(parts[0]), int(parts[1]))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


@dataclass(frozen=True)
class PatchRef:
    """A patch reference.

    Examples:
    - 6.6   -> end of patch 6.6
    - 6.6.5 -> mid-patch of 6.6 (21 days after patch start)
    """

    version: Version
    phase: int | None = None  # None => full patch, 5 => mid-patch

    @classmethod
    def parse(cls, s: str) -> "PatchRef":
        parts = s.strip().split(".")
        if len(parts) not in (2, 3):
            raise argparse.ArgumentTypeError(
                f"Invalid patch reference '{s}'. Expected like 6.6 or 6.6.5."
            )
        if not parts[0].isdigit() or not parts[1].isdigit():
            raise argparse.ArgumentTypeError(
                f"Invalid patch reference '{s}'. Expected like 6.6 or 6.6.5."
            )
        v = Version(int(parts[0]), int(parts[1]))
        if len(parts) == 2:
            return cls(version=v, phase=None)

        if not parts[2].isdigit() or int(parts[2]) != 5:
            raise argparse.ArgumentTypeError(
                f"Invalid patch reference '{s}'. Only '.5' is supported (mid-patch), e.g. 6.6.5."
            )
        return cls(version=v, phase=5)

    def __str__(self) -> str:
        if self.phase is None:
            return str(self.version)
        return f"{self.version}.{self.phase}"


def next_version(v: Version) -> Version:
    # User rule: exceptionally no 6.8 this year.
    if v.major == 6 and v.minor == 7:
        return Version(7, 0)

    # Normal rule: x.8 -> (x+1).0, otherwise x.(y+1)
    if v.minor == 8:
        return Version(v.major + 1, 0)
    return Version(v.major, v.minor + 1)


@dataclass(frozen=True)
class Patch:
    version: Version
    start: date

    @property
    def end(self) -> date:
        # 42-day patch: start .. start+41 (inclusive). Next patch starts at start+42.
        return self.start + timedelta(days=41)

    def contains(self, d: date) -> bool:
        return self.start <= d <= self.end

    @property
    def mid_start(self) -> date:
        # "Mid patch" starts 21 days after patch start (banner change).
        return self.start + timedelta(days=21)


def iter_patches_from(base: Patch) -> Iterable[Patch]:
    p = base
    while True:
        yield p
        p = Patch(version=next_version(p.version), start=p.start + timedelta(days=42))


def money(value: Decimal) -> str:
    q = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{q} EUR"


def wishes(primos: int) -> int:
    return primos // 160


def iter_days(start_inclusive: date, end_inclusive: date) -> Iterable[date]:
    d = start_inclusive
    while d <= end_inclusive:
        yield d
        d += timedelta(days=1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="calc-primo",
        description=(
            "Estimate Primogems and optional costs across future Genshin Impact patches. "
            "Assumes all rewards up to 'today' are already claimed."
        ),
    )

    horizon = parser.add_mutually_exclusive_group(required=True)
    horizon.add_argument(
        "--to-date",
        type=parse_date_ddmmyyyy,
        help="Forecast until this date (inclusive), format dd/mm/yyyy.",
    )
    horizon.add_argument(
        "--to-patch",
        type=PatchRef.parse,
        help=(
            "Forecast until the end of a patch reference (inclusive), e.g. 7.2 or 6.6.5 (mid-patch)."
        ),
    )
    horizon.add_argument(
        "--patches",
        type=int,
        help="Forecast for the next N patches, starting from the patch that contains tomorrow.",
    )

    parser.add_argument(
        "--today",
        type=parse_date_ddmmyyyy,
        default=None,
        help="Override today's date (for testing), format dd/mm/yyyy.",
    )

    parser.add_argument(
        "--no-blessing",
        action="store_true",
        help="Disable Blessing of the Welkin Moon (defaults to enabled).",
    )
    parser.add_argument(
        "--no-battle-pass",
        action="store_true",
        help="Disable Battle Pass (defaults to enabled).",
    )
    parser.add_argument(
        "--breakdown",
        action="store_true",
        help="Print a small breakdown by source.",
    )

    args = parser.parse_args(argv)

    today = args.today or date.today()
    start_date = today + timedelta(days=1)

    # Sync points (given by user examples):
    # 6.4 : 25/02/2026, 6.5 : 08/04/2026, 6.6 : 20/05/2026
    base = Patch(version=Version(6, 4), start=parse_date_ddmmyyyy("25/02/2026"))

    # Build patch list until we cover the horizon.
    patches: list[Patch] = []
    if args.patches is not None:
        if args.patches <= 0:
            parser.error("--patches must be >= 1")

        # Find the patch that contains tomorrow.
        for p in iter_patches_from(base):
            if p.contains(start_date):
                patches.append(p)
                break
            if p.start > start_date + timedelta(days=365 * 20):
                parser.error("Could not locate patch for the given date (unexpected calendar).")

        for _ in range(args.patches - 1):
            last = patches[-1]
            patches.append(
                Patch(version=next_version(last.version), start=last.start + timedelta(days=42))
            )
        end_date = patches[-1].end
    elif args.to_patch is not None:
        target: PatchRef = args.to_patch
        end_date: date | None = None
        for p in iter_patches_from(base):
            patches.append(p)
            if p.version == target.version:
                # End date depends on phase:
                # - full patch: inclusive end of patch
                # - mid patch: inclusive end of first half (day 20). Mid starts at day 21.
                if target.phase == 5:
                    end_date = p.mid_start - timedelta(days=1)
                else:
                    end_date = p.end
                break
            if len(patches) > 300:
                parser.error("Target patch too far in the future.")

        if end_date is None:
            parser.error("Target patch was not found.")
    else:
        end_date = args.to_date
        if end_date < start_date:
            parser.error("--to-date must be >= tomorrow (since today is assumed already claimed).")
        for p in iter_patches_from(base):
            # Keep patches that overlap the [start_date, end_date] window (for event dates).
            if p.end < start_date:
                continue
            if p.start > end_date:
                break
            patches.append(p)
            if len(patches) > 300:
                parser.error("Date range too far in the future.")

    use_blessing = not args.no_blessing
    use_bp = not args.no_battle_pass

    primos_free = 0
    primos_blessing = 0
    primos_bp = 0

    breakdown: dict[str, int] = {}

    def add(amount: int, kind: str, bucket: str) -> None:
        nonlocal primos_free, primos_blessing, primos_bp
        if bucket == "free":
            primos_free += amount
        elif bucket == "blessing":
            primos_blessing += amount
        elif bucket == "bp":
            primos_bp += amount
        else:
            raise ValueError(bucket)

        breakdown[kind] = breakdown.get(kind, 0) + amount

    # Daily commissions.
    day_count = (end_date - start_date).days + 1
    add(60 * day_count, "commissions (60/day)", "free")

    # Month-based recurring sources (free).
    for d in iter_days(start_date, end_date):
        if d.day == 1:
            add(800, "imaginarium (1st)", "free")
            add(800, "shop asterite (1st)", "free")
        if d.day == 16:
            add(800, "abyss (16th)", "free")
        if d.day in (4, 11, 18):
            add(20, f"connexion ({d.day}th)", "free")

    # Blessing: buy tomorrow, keep active continuously with 30-day renewals.
    blessing_cost = Decimal("0")
    if use_blessing:
        blessing_price = Decimal("3.32")
        purchase = start_date
        while purchase <= end_date:
            blessing_cost += blessing_price
            add(324, "blessing purchase (+324)", "blessing")
            for i in range(30):
                dd = purchase + timedelta(days=i)
                if dd > end_date:
                    break
                add(90, "blessing daily (+90)", "blessing")
            purchase = purchase + timedelta(days=30)

    # Patch-relative sources (free) and Battle Pass (paid).
    # We assume BP is purchased for the current patch (the patch that contains tomorrow),
    # and for each new patch that starts within the forecast window.
    # The primogem payout (1382) is still modeled at the end of the patch.
    bp_cost = Decimal("0")
    if use_bp:
        bp_price = Decimal("6.64")

    for p in patches:
        # If this patch doesn't overlap range, ignore.
        if p.end < start_date or p.start > end_date:
            continue

        if use_bp and (p.contains(start_date) or (start_date <= p.start <= end_date)):
            bp_cost += bp_price

        # Patch start rewards.
        if start_date <= p.start <= end_date:
            add(600, "patch change reward (+600)", "free")
            add(40, "trial characters start (+40)", "free")

        # Stygian: +10 days
        d = p.start + timedelta(days=10)
        if start_date <= d <= end_date:
            add(450, "stygian (+450, +10d)", "free")
            add(1000, "main event (+1000, +10d)", "free")

        # Trial characters: +20 days
        d = p.start + timedelta(days=20)
        if start_date <= d <= end_date:
            add(40, "trial characters mid (+40, +20d)", "free")

        # Side events: +25, +35 days
        d = p.start + timedelta(days=25)
        if start_date <= d <= end_date:
            add(420, "side event (+420, +25d)", "free")
        d = p.start + timedelta(days=35)
        if start_date <= d <= end_date:
            add(420, "side event (+420, +35d)", "free")

        # Livestream: 10 days before patch end
        d = p.end - timedelta(days=10)
        if start_date <= d <= end_date:
            add(300, "livestream reward (+300, end-10d)", "free")

        # End of patch.
        if start_date <= p.end <= end_date:
            add(100, "end of patch codes (+100)", "free")
            if use_bp:
                add(1382, "battle pass (end of patch +1382)", "bp")

    total_primos = primos_free + primos_blessing + primos_bp
    total_cost = blessing_cost + bp_cost

    total_days = (end_date - start_date).days + 1

    # Patch calendar display: show patches overlapping the range, plus the next patch start
    # if it falls within the horizon (useful for "date of each starting patch").
    patch_rows: list[Patch] = []
    for p in iter_patches_from(base):
        if p.end < start_date:
            continue
        if p.start > end_date:
            break
        patch_rows.append(p)
        if len(patch_rows) > 200:
            break

    print(f"Today:        {format_date_ddmmyyyy(today)} (assumed fully claimed)")
    print(f"From:         {format_date_ddmmyyyy(start_date)}")
    print(f"To:           {format_date_ddmmyyyy(end_date)}")
    print(f"Days:         {total_days}")
    print("")

    print("Patches:")
    if not patch_rows:
        print("  (none in range)")
    else:
        for p in patch_rows:
            tag = ""
            if p.contains(start_date):
                tag = "  (current)"
            mid = format_date_ddmmyyyy(p.mid_start)
            print(
                f"  {p.version}: {format_date_ddmmyyyy(p.start)} -> {format_date_ddmmyyyy(p.end)} (mid {mid}){tag}"
            )

    print("")
    print("Primogems:")
    print(f"  total:      {total_primos} ({wishes(total_primos)} wishes)")
    print(f"  free:       {primos_free} ({wishes(primos_free)} wishes)")
    print(
        f"  blessing:   {primos_blessing} ({wishes(primos_blessing)} wishes){'' if use_blessing else ' (disabled)'}"
    )
    print(
        f"  battlepass: {primos_bp} ({wishes(primos_bp)} wishes){'' if use_bp else ' (disabled)'}"
    )
    print("")
    print("Cost:")
    print(f"  blessing:   {money(blessing_cost)}")
    print(f"  battlepass: {money(bp_cost)}")
    print(f"  total:      {money(total_cost)}")

    if args.breakdown:
        print("")
        print("Breakdown:")
        for k in sorted(breakdown):
            print(f"  {k}: {breakdown[k]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
