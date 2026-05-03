
# calc-primo

Command-line script to estimate Primogems earned between dates / patches (Genshin Impact), including optional cost calculations for:

- Blessing of the Welkin Moon
- Battle Pass

Assumption: **today is already fully claimed**. The forecast starts **tomorrow**.

## Run

Examples (dd/mm/yyyy):

```bash
uv run python main.py --to-date 31/12/2026
uv run python main.py --to-patch 7.2
uv run python main.py --to-patch 6.6.5
uv run python main.py --patches 3
```

Disable paid sources:

```bash
uv run python main.py --to-patch 7.2 --no-blessing
uv run python main.py --to-patch 7.2 --no-battle-pass
uv run python main.py --to-patch 7.2 --no-blessing --no-battle-pass
```

Show a per-source breakdown:

```bash
uv run python main.py --to-date 31/12/2026 --breakdown
```

Override today's date (testing):

```bash
uv run python main.py --today 03/05/2026 --to-patch 6.6
```

## Patch calendar

Patch length is **42 days**.

Sync points used:

- 6.4 starts 25/02/2026
- 6.5 starts 08/04/2026
- 6.6 starts 20/05/2026

Version progression:

- normal: `x.y -> x.(y+1)`
- usually: `x.8 -> (x+1).0`
- exception: `6.7 -> 7.0` (no `6.8`)
