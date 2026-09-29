# Rules (v0.4)

Every statement in a core's own code comments, readme and shipped files is classified by the rules
below. The rules describe what a statement *says*; they never judge whether it is true (see "Taken
at face value" in the README).

## Hardware side

| Rule | Points | Fires on | Reasoning |
|---|---|---|---|
| Reports a measurement taken on the original PCB | +3 | a measurement word (measured, logic analyzer, oscilloscope) together with the original PCB/board and a stated value | The most direct evidence a comment can carry. Measurements of the MiSTer itself (SignalTap, M10K, build numbers) are excluded. |
| Notes where it differs from MAME | +3 | "unlike MAME", "differs from MAME", "MAME doesn't model / emulate / implement ...", "schematic and MAME disagree", "bug in MAME" | A stated difference means the developer had another reference and checked. Loose words near "MAME" (differ, bug, never) are not enough: "0 of 92160 pixels differ" is a MAME *match*. |
| Says it was checked against the original PCB | +2 | verified / tested / checked / confirmed against or on the PCB, original board, arcade hardware | Only an explicit original board counts. Negated statements ("not yet confirmed", "haven't checked it on the PCB") do not fire. |
| Ships hardware documentation files | +2 | schematic sheets, schematic PDFs, PAL/GAL equations in the core's own folder | Having the documents is stronger than citing them. Files in bundled libraries, bench/lab folders and MiSTer accessory boards (`hardware/`) are excluded. |
| Says it was checked on "real hardware" | +1 | verified / tested on real hardware, on HW | On MiSTer, "real hardware" often means the MiSTer board itself, so this counts less than an explicit PCB. Excluded when the context is the FPGA (SignalTap, DE10, CRT, M10K, simulation). |
| Cites hardware documentation that MAME's driver does not | +0.5 | schematic sheet/page, part numbers (74LS…, 82S…), Atari SP-/136xxx numbers, chip locations next to a chip word (PROM 7U, LS197 @5B), "based on the schematics" | Consulting documentation is not verification, so the weight is low. |
| Cites hardware references that MAME's driver also gives | 0 | as above, when *every* reference cited also appears in the MAME driver files for the same games (locations matched in any case, e.g. `dk3c.5l`) | Copying them from MAME would look the same, so they prove nothing. Shown, not counted; each links to the MAME line. |

## MAME side

| Rule | Points | Fires on | Reasoning |
|---|---|---|---|
| Says it was translated or ported from MAME | −3 | translated / ported / transcribed from MAME, "MAME 1:1", "based on MAME" | The developer's own account of the source. |
| Says it matches or was checked against MAME | −2 | matches / verified / tested / bit-exact / pixel-exact against MAME | MAME as the thing checked against. "Matching MAME convention" (a naming or polarity convention) does not count. |
| Keeps a MAME approximation | −1 | MAME's guess, hack, placeholder, surrogate, approximation kept | Where MAME itself notes a stand-in for unknown hardware. |
| Shares text with the MAME driver without saying so | −1 | a comment sharing a 6-word run with the MAME driver, in a module that does not declare a translation | Text carried over in a C++-to-HDL translation. Each item links to the MAME line it shares. |
| Cites MAME source | −0.5 | a MAME file, function or line reference | Using MAME as a reference is not the same as verifying against it, hence the low weight. |

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

- The MiSTer framework (`sys/`), release builds, and shared libraries (CPU cores such as T80,
  fx68k, TG68K; sound chips such as jt12, jt6295, jt5205; jtframe).
- ROM file names: MiSTer uses MAME's ROM sets by design, so matching names prove nothing.
- Memory addresses: a correct core must share them with any correct emulator.

## Closed-source cores

Coin-Op Collection cores get no reading and no needle: the method needs source code. Where the team
has published hardware research for a core's board (its Development-Documentation repository:
schematics, PCB layouts, board photos), that material is listed beside the core with links, and the
open-source components the team built (Development-Modules) are listed once for the group.

None of it is scored or coloured as hardware evidence, because it is one-sided by construction. For
an open-source core every statement is visible, including the MAME citations nobody chose to show;
for a closed core only what the team chose to publish is visible, and anything pointing at MAME
stays private. Scoring it would lean every closed core toward hardware for that reason alone.
Components are not attached to individual cores either: matching them through the chips in MAME's
driver proved unreliable (a ROM checksum containing "468705" matched a 68705; one driver file covers
many boards), and even a correct match would not show that the closed core uses the component.

## Known limitations

- Only what developers write down is visible. A carefully verified core with few comments reads
  "not enough evidence"; a heavily commented core that documents its MAME sources reads as MAME.
- All files in a repository are read, including side folders that are not part of the build.
  Restricting to the files the Quartus project compiles is planned.
- JTCORES builds are pinned to their source commit approximately (see README).

## History

- **v0.4** — hardware references cross-checked against MAME's driver (0 points when MAME already
  gives them; otherwise +0.5, was +1). "Real hardware" split out as a weaker rule; FPGA-context and
  negation vetoes; "differs from MAME" restricted to specific forms.
- **v0.3** — shipped documentation files counted; library/accessory files excluded; word-boundary
  fixes ("reported" is not "ported").
- **v0.2** — diminishing returns per module; modules without statements left out of the average.
- **v0.1** — calibration on seven cores.
