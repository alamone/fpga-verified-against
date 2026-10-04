# Structural review, batch 1: the prompt as run

Pasted into a Claude Code cloud session on this repository, branch `structural-batch-1`.

---

You are running batch 1 of a structural review of FPGA arcade cores. For each core in
`structural/batch1.json`, an independent reviewer reads the core's HDL at a pinned commit and
judges whether it is STRUCTURED like the original board (built from schematics or hardware
analysis) or like MAME's software emulation of that board. The rubric is
`structural/rubric.md`. Every reviewer follows it exactly.

## Rules for the whole session

1. **Stay blind.** This repository also holds a separate, text-based classification of the same
   cores. Neither you nor any reviewer may open `results/`, `RULES.md`, `README.md`, `data/`,
   `fva/`, `_layouts/` or `.github/`, or search the web for what anyone has said about a core.
   The point of this batch is an independent second reading; a reviewer who has seen the first
   one is no longer independent.
2. **Reviewers are independent of each other.** No reviewer sees another core's output.
3. **Write only under `structural/out/`.** Do not modify any other file in the repository.
4. **Commit and push to `structural-batch-1` only.** Never push to `main`, and never open a pull request.

## Setup (once)

Check out branch `structural-batch-1`, then fetch the sources into `/tmp/src`, outside the
repository, so nothing fetched can be committed by accident.

- **MAME, once for the whole batch:** a sparse checkout of `mame_repo` at `mame_commit`, limited
  to the directories of the `mame_files` that the batch lists:
  ```
  git clone --filter=blob:none --no-checkout --sparse <mame_repo> /tmp/src/mame
  cd /tmp/src/mame && git sparse-checkout set <the directories> && git checkout <mame_commit>
  ```
- **Each core:** fetch only the pinned commit:
  ```
  git init /tmp/src/<id> && cd /tmp/src/<id>
  git remote add origin <repo> && git fetch --depth 1 origin <commit> && git checkout FETCH_HEAD
  ```
  Cores sharing a repository at the same commit (several are in `jotego/jtcores`) can share one
  checkout. A core's files are at `<checkout>/<subdir>/<path from build_files>`; JT paths may
  climb out of the subdir with `../`, into shared modules.

If a fetch fails, retry once. If it still fails, write `structural/out/<id>.json` as
`{"id": "<id>", "error": "<what failed>"}` and move on.

## Running the reviews

Run one subagent per core, at most 5 at a time, all on the same model. Give every subagent
exactly this prompt, filling in the angle-bracketed fields from the batch entry, and nothing
more: no hints, no expectations, nothing about other cores.

> You are reviewing one FPGA arcade core. Read `<repo checkout>/structural/rubric.md` first and
> follow it exactly.
>
> Core: `<core>`
> Source: `/tmp/src/<id>/<subdir>` (commit `<commit>`)
> The files the build compiles, relative to that directory: `<build_files, one per line>`
> MAME files for comparison, under `/tmp/src/mame/`: `<mame_files, one per line>`
>
> Read only these sources and the rubric. Do not open anything else in the repository, and do
> not search the web.
> Write your JSON to `<repo checkout>/structural/out/<id>.json`, with `"id": "<id>"` and
> `"commit": "<commit>"`.

## After each review

Check that `structural/out/<id>.json` parses, has every field the rubric's Output section names,
has `lean` in −2..+2, and cites files that are in the core's file list. If it fails the check,
rerun that core once with a fresh subagent. If it fails again, keep the file and add `"invalid":
"<reason>"`.

After every 5 finished cores, commit `structural/out/` with the message
`structural: batch 1, <n>/40 done` and push, so a session that stops early loses nothing.

## When all 40 are done

Write `structural/out/SUMMARY.md` with one table row per core: id, lean, confidence,
comment_dependence, number of findings, and a one-line summary. Below the table, list any errors
and invalid outputs, then any rubric ambiguities that reviewers ran into, quoted from their
outputs. Do not compare against anything else in the repository; that comparison happens later,
outside this session. Commit, push, and stop.
