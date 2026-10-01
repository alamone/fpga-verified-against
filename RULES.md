# Rules (v0.7)

Every statement in a core's own code comments, readme and shipped files is classified by the rules
below. The rules describe what a statement *says*; they never judge whether it is true (see "Taken
at face value" in the README).

Comments are read as sentences, the way a person reads them: consecutive comment lines are joined,
a blank or decorative comment line (`====`, `----`) ends a paragraph, and table rows (columns lined
up with spaces, or `|` separators) are read one row at a time. A comment after code on the same line
stays on its own. Each rule counts at most once per sentence.

## Hardware side

| Rule | Points | Fires on | Reasoning |
|---|---|---|---|
| Reports a measurement taken on the original PCB | +3 | a measurement word (measured, logic analyzer, oscilloscope) together with the original PCB/board and a stated value | The most direct evidence a comment can carry. Measurements of the MiSTer itself (SignalTap, M10K, build numbers, SDRAM, PLL, clock-domain crossings) are excluded, and so are negated ones ("never been measured", "unmeasured"). |
| Notes where it differs from MAME | +3 | "unlike MAME", "differs from MAME", "MAME doesn't model / emulate / implement ...", "schematic and MAME disagree", "bug in MAME" | A stated difference means the developer had another reference and checked. Loose words near "MAME" (differ, bug, never) are not enough: "0 of 92160 pixels differ" is a MAME *match*. |
| Says it was checked against the original PCB | +2 | verified / tested / checked / confirmed against or on the PCB, original board, arcade hardware | Only an explicit original board counts. Negated statements ("not yet confirmed", "haven't checked it on the PCB", "unverified", "until that is confirmed") do not fire. |
| Ships hardware documentation files | +2 | schematic sheets, schematic PDFs, PAL/GAL equations in the core's own folder | Having the documents is stronger than citing them. Files in bundled libraries, bench/lab folders and MiSTer accessory boards (`hardware/`) are excluded. |
| Says it was checked on "real hardware" | +1 | verified / tested on real hardware, on HW | On MiSTer, "real hardware" often means the MiSTer board itself, so this counts less than an explicit PCB. Excluded when the context is the FPGA (SignalTap, DE10, CRT, M10K, simulation, SDRAM, PLL, clock-domain crossings) and when negated ("UNVALIDATED ON HARDWARE"). |
| Cites hardware documentation that MAME's driver does not | +0.5 | schematic sheet/page, part numbers (74LS…, 82S…), Atari SP-/136xxx numbers, chip locations next to a chip word (PROM 7U, LS197 @5B), "based on the schematics" | Consulting documentation is not verification, so the weight is low. |
| Cites hardware references or measurements that MAME's driver also gives | 0 | as above, when *every* reference cited also appears in the MAME driver files for the same games (locations matched in any case, e.g. `dk3c.5l`); and a reported measurement whose precise figures (three or more decimals, e.g. 55.4859 Hz) all appear there too. Crystal frequencies in MHz are not treated as such figures: they are part values every source prints. | Copying them from MAME would look the same, so they prove nothing. Shown, not counted; each links to the MAME line. |

## MAME side

| Rule | Points | Fires on | Reasoning |
|---|---|---|---|
| Says it was translated or ported from MAME | −3 | translated / ported / transcribed / taken / carried over from MAME, "From MAME src/…", "MAME 1:1", "based on MAME", "a port of MAME's …", "based on the … from MAME" | The developer's own account of the source. Not when negated: "read off SP-316 sheet 3 rather than taken from MAME" is the opposite, and so is "this replaced a port of MAME's core". |
| Says it matches, follows or was checked against MAME | −2 | matches / verified / tested / bit-exact / pixel-exact against MAME; "we follow MAME", "ground truth: MAME", "MAME's numbers are what we model" | MAME as the reference. "Matching MAME convention" (a naming or polarity convention) does not count. |
| Keeps a MAME approximation | −1 | MAME's guess, hack, placeholder, surrogate, approximation kept | Where MAME itself notes a stand-in for unknown hardware. |
| Shares text with the MAME driver without saying so | −1 | a comment sharing a 6-word run with the MAME driver, in a module that does not declare a translation; standard license notices (GPL, LGPL, BSD, MIT, Apache) do not count | Text carried over in a C++-to-HDL translation. Each item links to the MAME line it shares. |
| Cites MAME source | −0.5 | a MAME file, function or line reference | Using MAME as a reference is not the same as verifying against it, hence the low weight. A `.cpp` file named without the word MAME counts only when it can be MAME's: not a file of the core's own repository (unless MAME has a file of that name), not a testbench or generator (`tb_…`, `gen_…`, `…_ref.cpp`), not the MiSTer Main's (`user_io.cpp`, `menu.cpp`, …), and not in a comment naming another emulator such as Daphne. |

## Combining

- **Diminishing returns.** Within a module (one source file), each rule adds its points
  × log2(1 + times it fired): the tenth routine citation adds far less than the first.
- **Module position** = (hardware points + 1) / (all points + 2), from 0 (MAME) to 100 (hardware).
- **Core position** = the average over modules that contain statements, weighted by module size.
  The readme and the shipped documentation files each count like a quarter of the code.
- **Coverage** = the share of the core's own code that contains any statement. Modules with no
  statements are left out of the average, not counted as 50/50.
- **Confidence** from the total weighted points: under 5 insufficient (no needle), under 20 low,
  under 60 medium, otherwise high.
- **Reading**: under 40 "mostly MAME", over 60 "mostly hardware", otherwise "both".

## What is excluded

- HDL files the build does not compile: only the files named by the core's Quartus project (or,
  for JTCORES, its `cfg/files.yaml`) are the core's code. Side folders of notes, experiments or
  another board's variant are not read.
- The MiSTer framework (`sys/`), release builds, and shared libraries (CPU cores such as T80,
  fx68k, TG68K; sound chips such as jt12, jt6295, jt5205; jtframe), including the MiSTer
  high-score saver whether it sits in a `highscore/` folder or as a single `hiscore.v`.
- ROM file names: MiSTer uses MAME's ROM sets by design, so matching names prove nothing. Readme
  sentences about ROM sets, MRA files or zips are skipped for the same reason.
- Memory addresses: a correct core must share them with any correct emulator.

## Closed-source cores

Coin-Op Collection cores get no reading and no needle: the method needs source code. Where the team
has published hardware research for a core's board (its Development-Documentation repository:
schematics, PCB layouts, board photos), that material is listed beside the core with links, and the
open-source components the team built (Development-Modules) are listed once for the group.

None of it is scored or colored as hardware evidence, because it is one-sided by construction. For
an open-source core every statement is visible, including the MAME citations nobody chose to show;
for a closed core only what the team chose to publish is visible, and anything pointing at MAME
stays private. Scoring it would lean every closed core toward hardware for that reason alone.
Components are not attached to individual cores either: matching them through the chips in MAME's
driver proved unreliable (a ROM checksum containing "468705" matched a 68705; one driver file covers
many boards), and even a correct match would not show that the closed core uses the component.

The same "source not published" state covers any build whose design is not public: a developer
database build with no repository behind it, and a build whose repository holds only builds or MRA
files and no HDL (the note beside it says which). JTCORES is the exception to the second case: a JT
core can take its HDL from a sibling core's folder, so an empty folder there does not mean the
source is private.

## Known limitations

- Only what developers write down is visible. A carefully verified core with few comments reads
  "not enough evidence"; a heavily commented core that documents its MAME sources reads as MAME.
- The code itself is not judged. Whether the logic follows the hardware's structure (gates,
  counters and timing as on the schematic) or software's (MAME's functions and state carried over)
  would say more than any comment, but deciding it means reading each core's design, which a
  pattern-matching tool cannot do across 440 cores. The two code-level signals the analysis does
  compute (identifiers shared with the MAME driver, MAME-style read/write handler names) are not
  scored: a correct core shares many register and signal names with a correct emulator, so a name
  match alone does not show which one was copied.
- A core without a Quartus project or `cfg/files.yaml` where the tool looks for one (JTFRAME-style
  repositories outside jtcores, such as jlrh's and arcfpga, and a few others) is still read from
  every HDL file in its folder. Each core's row says which rule applied.
- Builds not committed to their source repository are pinned approximately, to the newest commit on
  or before the build's date (Slop Cores, one MeatCores); each says so beside its commit.

## History

- **v0.11** — after the Escape from the Planet of the Robot Monsters core's author replied that the
  core was checked against original PCBs, with MAME as a debugging aid. Its readme says so plainly
  and the rules missed it: "testing and benchmarking against an original dedicated cabinet and
  PCB" (the original or dedicated cabinet now counts as the original hardware; "my real cabinet"
  only weakly, since MiSTer users say it of the MiSTer in a cab), "Performance references are
  against actual machine gameplay, with MAME as the secondary reference" (now hardware-side), and
  "locked against real-cabinet captures". A game's own title is no longer text shared with MAME
  (Escape's header line matched the title in MAME's GAME() line), and "comparable to MAME's
  without assuming" is not a kept MAME assumption. Escape moved from 32 (mostly MAME) to 44
  (both); two other cores moved by one point.

- **v0.10** — after a core author's reply that comments saying "not MAME" were counted as MAME
  statements. v0.9 had fixed the plain "…, not MAME" form; his own Irem cores showed more. Files
  named under a core's own tool folders (`sim/alu.cpp`) are the developer's, also where the same
  name appears bare (`alu.cpp::kDiv`): ten of Irem M72's simulator references were scoring as
  MAME citations. "MAME is NOT the oracle for …", "MAME doesn't update these flags, but
  documentation says it should" and "MAME's model is not a model of this circuit" depart from
  MAME; "NOT MAME's … approximation" rejects the approximation rather than keeping it. MAME's
  input-port and DIP-switch definitions copied into a comment (`PORT_DIPNAME`, `PORT_BIT`) no
  longer count as shared text: they document the game's settings, which any correct core shares.

- **v0.9** — a sweep for misclassified statements rather than one fix at a time. Readmes are read
  as paragraphs, as comments have been since v0.6: Tempest's "Use the supplied Tempest MRA with the
  matching MAME / Tempest Rev 3 ROM set" was split at the line break and scored as verified against
  MAME, the one line that made Tempest "mostly MAME" against 13 hardware statements. The MiSTer
  high-score saver (`hiscore.v`, in 85 cores) is framework, like the `highscore/` folder already was;
  its "MAME hiscore.dat support" line scored as a MAME citation. Comments that say something is
  *not* from MAME ("This follows the SCHEMATIC, not MAME", "rather than from MAME's") no longer
  count as citing it, and "the schematics document something MAME's model does not" and "MAME
  drivers get wrong" count as departures. On the hardware side, HDMI and scaler output are MiSTer
  context ("HDMI rotation: done, confirmed on hardware"), a Quartus or simulation netlist is not a
  board netlist, and "a PCB measurement should settle it" is not a measurement. 117 of 362 scores
  changed, 12 readings: Tempest and Robotron (mostly MAME to not enough evidence), Vastar, Bagman and
  Sega System 1+2 (likewise, their MAME evidence was the high-score line), Bosconian and Trio The
  Punch (mostly MAME to both), XSleena, Tutankham and jtkunio (both to mostly hardware), Arabian
  and Kangaroo (both to mostly MAME, 39, once the high-score module no longer averaged in).

- **v0.8** — a `.cpp` file name is no longer a MAME citation by default. Any `something.cpp` used
  to count, so Daphne's `lair.cpp` and `ldp1000.cpp` (Laserdisc Games), the developers' own
  testbenches (`sim/tb_r2crypt.cpp`), the MiSTer Main's `user_io.cpp`, and Astrocade's "Auto-generated
  by gen_votrax_roms.cpp" ROM tables all scored as citing MAME: 93 items in 24 cores. Files a core
  ships that MAME also has (DECO Cassette carries `decocass_m.cpp`) still count. Also: "a port of
  MAME's …" and "based on the … from MAME" now count as stated MAME sources, as "ported from MAME"
  already did; Astrocade's Votrax speech chip says both. 13 of 362 scores changed, one reading:
  Donkey Kong (not enough evidence to both, 47; its sound circuits say they are drawn from MAME's
  discrete models). Astrocade moved from 37 to 19 and Q*bert from 35 to 26, both still "mostly MAME".

- **v0.7** — standard license notices no longer count as text shared with MAME. Breakout's GPL
  header matched the one in MAME's `nl_breakout.cpp` and scored as eight copied comments; the
  canonical wording of the common notices is now removed from the comparison (a keyword filter
  would also have dropped real comments that mention a license). Two cores changed: Breakout
  (47 to 60, still not enough evidence) and Pong (56 to 62, both to mostly hardware).

- **v0.6** — comments are read as sentences instead of line by line. A sentence wrapped across lines
  used to lose its second half: Raiden II's "Until that is confirmed on hardware we / follow MAME"
  scored as hardware verification. Also: "unvalidated / unverified" and "until … confirmed" are
  negations; a PCB measurement whose figures MAME's driver already gives is neutral (Raiden II's
  "VSync 55.4859 Hz" is MAME's own note); "we follow MAME", "ground truth: MAME", "taken / carried
  over from MAME" and "From MAME src/…" count on the MAME side; the MiSTer's SDRAM, PLL and
  clock-domain crossings are FPGA context. Three older misfires fixed in the same pass: "dumped"
  alone ("data dumped via the NVRAM interface") is no longer hardware documentation, it needs a
  chip word beside it; "@ 0X" is a hex prefix, not a board location; "MAME ignores it, and so
  should we" agrees with MAME rather than departing from it. 10 of 443 readings changed: four
  JTCORES cores gained PCB measurements that had been split across lines, four cores gained stated
  MAME sources, and Seta Downtown, Kiki Kaikai, Dogyuun and Grind Stormer lost hardware credit they
  should not have had. Raiden II (spacestate1) moved from 35 to 25, still "mostly MAME".

- **v0.5** — only the files a build is made from count as the core's code: the files its Quartus
  project compiles (the `.qsf` and the `.qip` files it includes), or for JTCORES the files its
  `cfg/files.yaml` lists, including HDL taken from sibling cores (Paroda, Ninja). Side folders
  (notes, experiments, another board's variant) no longer count. 25 of 443 readings changed, mostly
  JTCORES cores that now include the sibling-core code they use.
- **v0.4** — hardware references cross-checked against MAME's driver (0 points when MAME already
  gives them; otherwise +0.5, was +1). "Real hardware" split out as a weaker rule; FPGA-context and
  negation vetoes; "differs from MAME" restricted to specific forms.
- **v0.3** — shipped documentation files counted; library/accessory files excluded; word-boundary
  fixes ("reported" is not "ported").
- **v0.2** — diminishing returns per module; modules without statements left out of the average.
- **v0.1** — calibration on seven cores.
