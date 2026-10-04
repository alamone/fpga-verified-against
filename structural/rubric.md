# Structural review rubric (v1)

Unchanged from the 2026-10-01 pilot (16 labelled cores, 15 agreed; a comments-stripped rerun of
three cores gave the same verdicts), except the Output section now names the core and commit.

Question: is this FPGA arcade core STRUCTURED like the original board (built from schematics /
hardware analysis) or like MAME's software emulation of it (logic carried over from MAME's C++
driver)? Judge the CODE, not what anyone says about it.

## Ground rules

1. **Do not use comments, READMEs or docs as evidence of provenance.** Statements like "ported
   from MAME", "verified on PCB", "from schematic sheet 3" are exactly what this review must NOT
   rely on; another tool already counts those. Comments may help you understand what a block
   does; the evidence must be the code's structure. If a finding only holds because of a comment,
   drop it.
2. **Ignore shared libraries**: CPU cores (T65, TG68K, fx68k, T80, nec/v33, z8002, mb88), sound
   chips (jt51, jt12, TMS5220, OKI), the MiSTer framework, SDRAM/DDR controllers, ROM loaders,
   PLLs, save states, debug/test-pattern/self-test modules. They say nothing about this board.
3. **FPGA engineering is neutral.** Time-multiplexing, SDRAM caches, clock enables from a fast
   system clock, serialized arithmetic to save DSPs, line buffers in BRAM: every FPGA core does
   these for resource reasons. Do not count them either way.
4. You MAY read the MAME driver files listed for this core and compare: does the HDL mirror the
   driver's decomposition, control flow, data layout or names, or does it diverge from MAME in
   the way the physical board would?
5. Every finding cites a file and line range (or module name) in the CORE. Findings about MAME
   cite the MAME file and function too.

## Signals

Toward HARDWARE structure (+):
- Module/block boundaries follow physical chips or schematic blocks (a module per custom chip,
  per PAL, per counter chain, per line buffer pair), with the chip's own pins as ports.
- Logic expressed as the board's gates/counters/latches: counter chains with carry/load like
  74161s, PAL equations as sum-of-products, registered latches strobed by decoded signals.
- Timing derived from the board's own clocks and raster counters (H/V counter bits driving
  fetch phases, pixel-by-pixel pipelines whose stages line up with the board's pixel clock).
- Behavior MAME does not model, implemented the way hardware would produce it (bus contention,
  wait states, per-pixel priority from PROM lookups, open-bus values).
- Naming from the board's signal/net names (H1/H2/H4, /VBLANK, CPUINT, chip pin names).

Toward MAME structure (−):
- Module decomposition mirrors MAME driver functions (draw_sprites, screen_update, tile_info
  callbacks, address-map handlers `*_r` / `*_w`) or MAME device classes.
- Control flow transliterated from C: a state machine whose states step through the same loop
  as a MAME function (for each sprite, for each row...), same order of operations, same
  variable names, same bit-twiddling expressions.
- Rendering done per frame / per line in a batch that reproduces MAME's draw order rather than
  the board's scan-time pipeline (where the board scans per pixel).
- Data layout and register semantics expressed in MAME's abstractions (MAME's memory map
  regions, MAME's tilemap/gfx-decode conventions as the organizing structure).
- Constants and tables identical to MAME's that the hardware would express differently.

Mixed / neutral: CPU memory maps (both sides must match), ROM layouts, register addresses,
anything a correct core must share with a correct emulator.

## Procedure

Budget your reading: start at the top-level core module, then read the 4–8 modules that carry
this board's own logic (video pipeline, sprite engine, priority/mixer, address decode, custom
chips). Skim the rest. Compare against the matching MAME functions where useful.

## Output

Write a JSON file to the path you are given:

{
  "id": "the batch entry's id",
  "commit": "the commit you reviewed",
  "lean": -2..+2,            // -2 clearly MAME-structured, 0 mixed/unclear, +2 clearly hardware-structured
  "confidence": "low|medium|high",
  "summary": "2-4 sentences, plain language",
  "findings": [
    {"side": "hw|mame|neutral", "signal": "short name", "where": "file:lines or module",
     "mame_ref": "optional MAME file:function", "note": "what in the code shows it (1-2 sentences)"}
  ],
  "comment_dependence": "none|some|heavy",   // honest: how much did comments steer you anyway?
  "files_read": ["..."]
}

Aim for 6-12 findings, the strongest ones. Prefer specific over general.
