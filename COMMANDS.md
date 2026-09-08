# Building a Command

What a command file is made of, and what every flag costs to support. Read the flag table before
adding a command, and again before changing one. A flag a command could carry but does not is the
most common gap in this codebase, and the two-line kind is easy to miss.

`src/commands/template.txt` is the starting point. Copy it rather than an existing command.

---

## The contract

`utils/files.get_command_modules()` walks `src/commands/*/` and registers the one `Command`
subclass it finds in each file. A file is reachable purely by existing, so there is nothing to
register by hand. Each file holds three things:

| Piece | What it is |
|---|---|
| `info = CommandInfo(...)` | Help metadata: name, aliases, description, parameters, examples |
| One `Command` subclass | The `@commands.command` entry point, plus `supported_flags` |
| A module-level `run()` | The work, so other commands can call it |

`-day`, `-week`, `-month` and `-year` are all thin wrappers over `commands.summary.races.run`.
That is what the module-level `run()` is for.

The subdirectory a file lives in is the group `-help` displays it under. A directory with no
modules becomes an empty group.

---

## Flags

Flags are parsed in `bot_setup.parse_flags` before dispatch, stripped out of the message, and
handed to the command as `ctx.flags`. Three things come out of that:

- **`ctx.flags`** is the resolved `Flags` dataclass, defaults filled in.
- **`ctx.explicit_flags`** maps flag name to the token the user actually typed. Defaults the user
  never typed do not appear.
- **`ctx.raw_args`** is the original tokens after the command name, before any stripping. `-search`
  reads this, which is why `-lf fr` searches for the text "fr" rather than filtering to French.

### Declaring support

```python
class MyCommand(Command):
    supported_flags = {"raw", "gamemode", "status", "language", "date_range"}
```

**Every command declares `supported_flags`.** Omitting the line means the command warns on every
flag a user passes. A command with no data path at all sets `ignore_flags = True` instead, which is
what the account commands do.

Declaring a flag is a promise that the command honours it. `cog_before_invoke` warns and resets
anything not declared, so an undeclared flag is safe. A **declared** flag that the command then
ignores is silently wrong output, and nothing catches it.

### The table

"Free" means the flag works the moment you declare it, as long as your data comes from a function
that takes `flags=ctx.flags`. Anything else needs the wiring named in the last column.

| Flag | Tokens | Free when it comes from | Otherwise you must |
|---|---|---|---|
| `metric` | `pp`, `wpm` | never free | read `ctx.flags.metric` yourself |
| `raw` | `raw` | `get_races`, `get_quote_bests`, `get_quotes_over_leaderboard` | swap the column or field yourself |
| `gamemode` | `solo`, `quickplay`, `lobby` | those three, plus the `match_results` queries | pick the table and filter yourself |
| `status` | `ranked`, `unranked`, `any` | same as `gamemode` | apply the pp bounds yourself |
| `language` | 17 ISO codes | same as `gamemode` | join `quotes` and filter, or send a universe to the API |
| `number` | `500`, `1,234`, `2k`, `1.5k` | never free | read `ctx.flags.number` yourself |
| `number_range` | `>150`, `<120`, `100-150` | never free | pass `min_wpm` and `max_wpm` as arguments |
| `date` | one date token | never free | read `ctx.flags.date` yourself |
| `date_range` | two date tokens, or a period word | `get_races`, `get_quote_bests` | filter on `timestamp` yourself |
| `quote_id` | a quote ID, a solo URL, `^`, `daily` | never free | resolve through `self.get_quote(ctx, ...)` |

Aliases resolve through `OPTION_ALIASES` in `utils/strings.py`: `qp`, `mp`, `multi` and
`multiplayer` all mean `quickplay`, `ur` means `unranked`, and the period words take `d`, `w`,
`wk`, `m`, `mo`, `y` and `yr`.

---

## What each flag actually does

### `metric`

`pp` or `wpm`, defaulting to `pp`. Nothing in the data layer reads it. The command chooses what to
select and what to label.

**Trap:** `parse_flags` forces `metric` to `wpm` whenever `status` is not `ranked`, because pp is
meaningless outside ranked races. A command offering `metric` and `status` together gets that
coupling whether it wants it or not.

### `raw`

Swaps the real numbers for the ones before error correction. The three data functions that honour
it alias `rawWpm as wpm` and `rawPp as pp`, so the calling code reads `race["wpm"]` unchanged and
gets the raw value. They also reorder on the raw column when `order_by` was `pp` or `wpm`.

Everywhere else, swap the column yourself. The precedents:

- A bespoke query takes a `raw` parameter and picks its column, like `get_best_by_length`.
- Keystroke data carries both series on `ProcessResult`, so read `keystrokeRawWpm` instead of
  `keystrokeWpm`. `commands/graphs/racecompare.py` is the reference.
- A command building a fresh `Flags(...)` rather than passing `ctx.flags` threads `raw` through by
  hand, like `commands/graphs/pplength.py`.

**Say so in the title.** Raw changes what the numbers mean, and a page with no marker is
indistinguishable from a normal one. A `flag_title=True` page gets "(Raw)" for free. Anything else
appends it by hand.

**On a board, ask how much of it you hold.** The API sorts on `wpm` and returns no `rank` field, so
ranks come from enumerating the rows. Swapping the column alone relabels the rows without reordering
them, which is wrong either way. Re-sorting locally is only honest when the fetch is deep enough that
nobody outside it belongs in the view. `-dailyleaderboard` and `-dailygraph` fetch `results=100` and
show ten, so a re-sort is accurate to 100 places. `-quoteleaderboard` reads
`GET /v1/quotes/{quoteId}`, which returns exactly ten rows and takes no size parameter, so re-sorting
those ten would miss anyone whose raw score belongs in the top ten but whose real score did not
place. That is why it has no `raw`.

**Do not add `raw` to a command that already shows raw as its own field.** `-races`, `-average`,
`-racegraph`, `-segments`, `-matchgraph` and `-encounters` each render a raw section beside the
real one. A flag there duplicates what is already on screen.

The GG+ gate on **raw pp** is inconsistent across the stack and there is no rule to follow yet.
`-best` and `-worst` refuse outright, `-racegraph` swaps the one value for `GG_PLUS_LINKED`, and
seven graph commands show it to everyone.

### `gamemode`

`solo`, `quickplay` or `lobby`, defaulting to None, which means every race. The two multiplayer
values switch `get_races` and `get_quote_bests` from `races` to `multiplayer_races` and drop `dnf`
and `quit` rows. `solo` adds `matchId IS NULL` to the solo table.

### `status`

`ranked`, `unranked` or `any`, defaulting to `ranked`. It reaches SQL as a pp bound rather than as
a column: ranked is `pp > 0`, unranked is `pp <= 0`, any is `pp > -1`.

### `language`

The universe selector, not just a filter. Seventeen codes live in `LANGUAGES`, and eleven of those
are universes with their own ranked pool and pp board, listed in `config.UNIVERSE_CODES`. A code
that is not a universe stays a plain unranked filter inside English.

Locally, the data functions join `quotes` and filter `q.language` on the display name.

Against the API, use `take_universe(ctx)` from `commands/base.py`. **The API rejects a
non-universe code with a 400 rather than falling back to English**, so never send
`str(flags.language)` directly. `take_universe` warns the user, clears the flag and returns None
when the language has no universe of its own.

Display is free on a `flag_title=True` page, since `get_flag_title` appends the language name.
`-stats` has no title to hang one on, so it puts the universe in the footer instead.

**Declaring `"language"` is also what preserves a stored universe.** `cog_before_invoke` clears
`ctx.flags.language` for any command that does not declare it, above the `ignore_flags` early
return, then warns that the stored universe had no effect.

Two API endpoints take a universe: `GET /v1/users/{userId}` and `GET /v1/leaders`. The leaders
board accepts eight sorts and only `gamemode=any`, and anything else is a 400, so check before
sending.

### `number` and `number_range`

`number` is a single integer. It accepts `1,234`, `2k` and `1.5k`, and a leading `-` makes it
negative, which is how `-racegraph -1` reaches the second-to-last race. `1_000` is a username, not
a number.

`number_range` is a `(min, max)` tuple from `>150`, `<120` or `100-150`, either end None. It does
not travel inside `Flags` to the data layer. Pass it as the `min_wpm` and `max_wpm` arguments to
`get_quote_bests`.

### `date` and `date_range`

`date` is a single date token, and it is **never None**. `parse_flags` runs `parse_date` over it
unconditionally, so a command reading `ctx.flags.date` with nothing typed sees now().

`date_range` is either two date tokens or one period word, resolved in `bot_setup.set_user` against
the user's stored time-travel range and their timezone. A stored range applies with nothing typed,
which is why `cog_before_invoke` clears it for undeclaring commands above the `ignore_flags` return.

Only `get_races` and `get_quote_bests` honour it. **`-encounters` declares `date_range` and none of
its three `match_results` queries filter on `timestamp`**, so time travel silently returns all-time
results there. That is the failure this table exists to prevent.

Show an active range with `range_subtext(ctx)`, which returns an empty string when there is none.

Declaring `date` suppresses the warning about a redundant second date, since a command reading one
date ignores the rest rather than being wrong about them.

### `quote_id`

A real quote ID, a `typegg.io/solo/...` URL, `^` for the last quote seen in the channel, or
`daily`. Resolve it with `self.get_quote(ctx, quote_id)`, which handles all four forms and records
the quote as the channel's recent one.

**Trap:** recognising a bare quote ID costs one `SELECT` per unrecognised token on every command
invocation, because `parse_flags` cannot tell a quote ID from a username without asking.

---

## Warnings the base class emits

`Command.cog_before_invoke` runs before every command and produces at most three subtext lines:

| Situation | Line |
|---|---|
| The user typed a flag the command does not declare | ``-# :warning: `raw` has no effect on this command`` |
| A stored time-travel range, on a command without `date_range` | `-# :warning: time travel has no effect on this command` |
| A stored universe, on a command without `language` | `-# :warning: your universe has no effect on this command` |

An unsupported flag is also reset to its default, so the command body never sees it.

`take_universe` adds a fourth, for a language with no universe of its own:

```
-# :warning: Latin has no universe of its own
```

---

## Checklist for a new command

1. Copy `src/commands/template.txt` into the subdirectory matching its help group. The file name
   matches the command name.
2. Fill in `info`, and update the class and method names.
3. Walk the flag table above. For each flag, decide whether the command can honour it, and declare
   the ones it can. A command with no data path sets `ignore_flags = True` instead.
4. Check that every declared flag reaches the data. Pass `flags=ctx.flags` where a function takes
   it, and wire the rest by hand.
5. Mark `raw` and the active universe in the title, unless the page is already `flag_title=True`.
6. Add the invocation to `INVOCATIONS` in `tests/test_command_smoke.py`, one line per flag
   combination worth pinning. A command left out must appear in `SKIPPED` with a reason, or the
   coverage test fails.
7. Run the gates.

```bash
ruff check src tests tools
pytest
pytest -m slow
cd src && python -c "import bot_setup, tasks, error_handler, web_server.server"
```
