# fpga-verified-against

What does each FPGA arcade core say it was verified against: the original hardware, or MAME?

FPGA cores are valued for reproducing the original hardware. A core built and checked against
schematics, dumped PALs and measurements of the real board does that; a core checked only against
MAME can at best reproduce MAME, including MAME's guesses. Both kinds exist, and from the outside
they look the same. This project reads each core's **own** source code, comments, readme and
shipped documentation, and summarizes what they say, with every statement linked so readers can
check it themselves.

**[View the results](https://alamone.github.io/fpga-verified-against/results/)**

The results page shows one meter per core:

```
MAME  |--------------------|  Hardware
```

Statements pointing to MAME pull the needle left; statements pointing to the original hardware pull
it right. A core whose code says too little either way gets an outlined bar and no needle ("not
enough evidence"). A core whose source is not published gets a dashed outline ("source not
published").

## Taken at face value

Everything shown is what the developers themselves wrote. It is not independently checked: a core
may be verified more, or less, than its comments say. Open source makes a false claim easy to
expose, which is why developers' own words are a reasonable starting point. Readings describe the
evidence in the code; they are not ratings of the cores or their authors.

This method reads source code, so closed-source cores cannot be assessed this way and are listed
separately. Black-box testing against the original hardware or MAME would still be possible, but is
far more work and is not done here.

## What is covered

Every arcade core in the three databases [update_all](https://github.com/theypsilon/Update_All_MiSTer)
installs by default:

- **MiSTer official distribution**: each build is traced through the MiSTer wiki's core list to
  its repository and the exact commit that added it.
- **JTCORES** (Jotego): builds are traced to their folder in `jotego/jtcores`. The builds do not
  record their source commit, so the analysis is pinned to the newest commit before publication and
  marked approximate.
- **Coin-Op Collection**: distributed as builds only; shown as "source not published". Hardware
  research the team has published for a core's board is listed beside it, neutrally and never
  scored, since only what they chose to publish is visible (see [RULES.md](RULES.md)).

Plus the arcade cores in databases individual developers publish, which users add to update_all by
hand (a section in `downloader.ini`): **MeatCores** (meathax), **Slop Cores** (TheJesusFish),
**kuzecores** (kuzearcade), **jlrh**, **arcfpga** (bmo00) and **blahm1d**. Each build is traced to
the developer's own repository: exactly where the database or the repository gives the build file,
otherwise to the newest commit on or before the build's date, marked approximate. Builds with no
public repository behind them are shown as "source not published". rmCores is not listed separately:
it rebuilds official cores, which are already covered. These databases were found through
[MisterZine](https://misterzine.fyi/releases/)'s source list and a GitHub search.

Not covered yet: cores published only as a repository, with no database (for example
[ika-musume](https://github.com/ika-musume)'s CV1000 core).

Each core is compared with the MAME driver for the games it loads (from the ROM set names in the
MRA files the databases ship).

## How the needle is placed

See [RULES.md](RULES.md) for every rule, its points and the reasoning behind it. In short: specific,
checkable statements count most (a measurement on the original PCB, a documented difference from
MAME, schematics shipped with the core); a hardware reference that MAME's own driver already gives
counts for nothing, since copying it from MAME would look the same; "checked on real hardware",
which on MiSTer often means the MiSTer board itself, counts less than an explicit mention of the
original PCB.

## Running it

Python 3.10+ and git; no other dependencies.

```bash
python -m fva all        # sources -> fetch -> analyze -> report
```

or step by step: `sources` (which builds exist and their commits), `fetch` (check out the code at
those commits, plus MAME's drivers), `analyze` (-> `results/results.json`), `report`
(-> `results/index.html`). Downloads go to `work/`, which is not committed.

## For core developers

If a reading misrepresents your core, please open an issue. Point at the statement that misleads it,
or add a note on how the core was verified; responses will be shown alongside the evidence. Rules
are versioned, and a rule that misreads real comments gets fixed for every core.

## Licenses

- The tool (`fva/`) is under the [MIT License](LICENSE).
- The results (`results/`) are under [CC BY 4.0](LICENSE-results.md): reuse freely with attribution.
- Quoted excerpts from cores remain under their authors' own licenses, and are quoted for
  commentary with a link to the original line. MAME source is linked, not copied.
