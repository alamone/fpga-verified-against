# Structural review, batch 1: summary

40 cores, each reviewed by an independent subagent against `structural/rubric.md` (v1) at the pinned commits in `structural/batch1.json`.
Lean runs from −2 (clearly MAME-structured) to +2 (clearly hardware-structured). Per-core detail is in `structural/out/<id>.json`.

| id | lean | confidence | comment_dependence | findings | summary |
|---|---|---|---|---|---|
| Escape | -1 | medium | some | 12 | Scan-time fetch and line-buffered sprites, but the palette formula, stain logic, two-pass merge and pen arithmetic are MAME's. |
| jtgng | +2 | high | some | 12 | Board-style H/V counters drive scan-time tile and sprite pipelines; sprite DMA takes the 6809 bus; only the bank-select expression echoes MAME. |
| Vindicators | +2 | high | some | 12 | Motion-object sequencer written as PAL equations on H phases, time-sliced VRAM, LS163-style DTACK and gate-level priority. |
| PolePosition | -2 | high | some | 11 | Sprite, road, mixing, palette and custom-chip logic follow MAME's polepos driver and device code term for term. |
| Fuuki | -2 | high | some | 11 | Video rebuilt from MAME's tilemap and sprite devices: priority masks, scroll maths, layer table and zoom arithmetic are MAME's. |
| Arcade-Atari-G1_(Gm0rk) | -2 | high | some | 12 | Motion-object engine split one module per function of MAME's atarirle device, with its sort, scaler and erase bookkeeping. |
| freeze | -1 | medium | none | 10 | Small core split by function; address decode, sprite walk order and RAM layout follow MAME's jack driver; no board structure. |
| LadyBug | +2 | high | some | 11 | Chip- and gate-level model: TTL instances, counter-chain timing, scan-time tile fetch and WAIT-based bus contention. |
| CanyonBomber | +2 | high | some | 11 | Gate- and counter-level model: scan-time motion objects, 74xx counters and shift registers, board-style sync and sound. |
| Chameleon | -2 | high | none | 11 | One per-frame state machine draws tiles then sprites into a frame buffer, in MAME's order and with MAME's field decoding. |
| Arcade-Gyruss_(MrX-8B) | 0 | medium | none | 12 | Scan-time video leans hardware, but the modules are not split by chip, and the sound timer and raster numbers are MAME's. |
| jtgunsmk | +2 | medium | some | 11 | Shared Capcom blocks: bus-request sprite DMA, per-line sprite search, counter-chain draw and raster-derived interrupts. |
| jtcomsc | +1 | medium | some | 11 | 007121 chip module with per-pixel priority and bit-level 007452 maths; the per-line engines themselves are generic FPGA work. |
| jttoki | -1 | medium | none | 11 | Generic jtframe layer engines; sprite tests, address decodes and the ADPCM interface follow MAME's handlers and draw_sprites. |
| MissileCommand | +2 | high | some | 10 | Split into the board's circuit blocks: 7442 decode, PHI0-clocked MADSEL, per-bit VRAM write enables, shifted video. |
| Arkanoid | +2 | high | some | 11 | Netlist-style rebuild: the MB112S146 as a pin-level module, IC-numbered instances, and contention driven by H counter bit 0. |
| jtflane | +1 | medium | some | 10 | 007121 chip model with per-line fetch and per-pixel priority; the 051733 maths chip uses MAME's names and read case. |
| Arcade-PenguinKunWars_(MrX-8B) | +1 | medium | none | 11 | Scan-time background, PROM colour path and line-buffer wrap lean hardware; the ROM line swap and interrupt hold copy MAME. |
| TaitoAir_1.0_(retrogarage) | -2 | high | some | 13 | Polygon parser and rasterizer, gradient, sprites and DSP peripherals are MAME's Taito Air code expressed as RTL. |
| AtariTetris | -1 | medium | none | 10 | Little board logic; slapstic constants and state machine and the IRQ schedule follow MAME, and the playfield fetch is generic. |
| Druaga | +1 | medium | some | 11 | Scan-time tiles and per-line sprites lean hardware; the I/O chip follows MAME's namcoio and sprite names follow MAME. |
| Arcade-SKNS_(srg320) | +1 | medium | none | 12 | One module per Kaneko chip with scan-time pipelines; the HIT collision chip, region lock and blend maths port MAME. |
| Arcade-SuperCobra_(gaz68) | +2 | high | some | 12 | Board model: LS259 latch, H-bit object timing, live star LFSR, resistor-style colour sum and a chip-by-chip audio board. |
| jtbtiger | +2 | medium | some | 11 | Capcom-style counters, bus-request sprite DMA, per-line sprite scan and PROM priority; the MCU is wired by its pins. |
| Arcade-DemoDerby_(alanswx) | +2 | medium | some | 11 | Counter-driven tile fetch, per-line sprite line buffers and an SSIO sound board built from counter cascades. |
| Arcade-Garegga_(zakk4223) | -2 | high | none | 12 | GP9001 handling, sync windows, offsets, decode names, sound banking and text layer all reproduce MAME's code. |
| jtlabrun | +1 | medium | some | 11 | 007121 chip module with per-pixel priority and raster interrupts; no gate-level structure; the 051733 maths chip is MAME-like. |
| Arcade-BlackWidow_(derpyder) | +1 | low | some | 9 | Small board logic with a counter-chain IRQ and block decodes; the AVG matches neither side (MAME's AVG not provided). |
| jttrack | +1 | medium | some | 12 | Per-line row scroll from object RAM, adder-based scroll and sprites, a decoder-cascade map; generic shared modules. |
| jtcop | +2 | medium | some | 12 | Priority PROM, BAC06 chip modules sharing counters, vblank-timed sprite copy, bus waits; protection table copied from MAME. |
| Darius | -2 | high | some | 12 | Priority, draw order, sprite arithmetic, audio gains, address decode and triple-screen offsets follow MAME's driver. |
| SegaXBoard | -2 | high | some | 12 | Chip modules line up with MAME devices; sprite, road, mixer and tilemap logic are MAME's C++ turned into state machines. |
| Arcade-NamcoS2_STD | -2 | high | some | 12 | Per-line re-expression of MAME's namcos2 driver: draw order, shadow mix, ROZ special cases and timer-based events. |
| Arcade-KonamiGX_(ppriest) | -2 | high | some | 13 | Interrupts, ESC protection, sprite colour and priority, mixer and per-game table follow MAME; vendored chip models bent to MAME. |
| Rayforce_(spacestate1) | -2 | high | some | 12 | Video modules map one-to-one onto taito_f3_v.cpp functions and reuse their expressions, constants and hacks. |
| jtexed | +2 | high | some | 10 | Capcom board layout: priority PROM, bus-request sprite DMA, per-line sprite pick, IRQ PROM and wired scroll addressing. |
| jtflstory | +2 | medium | some | 12 | Per-line sprite scan writing back to object RAM, palette-RAM priority, MCU bus mastering and shared-bus arbitration. |
| Tutankham | 0 | medium | some | 11 | Board-shaped shell and live starfield LFSR, but the framebuffer readout, address decode and star logic copy MAME. |
| Arcade-DonkeyKong3_(gaz68) | +2 | high | some | 10 | Chip-by-chip netlist: PROM plus 74xx138/139 decode, WAIT from VRAMBUSY, chip-named sprite and tile pipelines. |
| SlapFight | +2 | high | some | 11 | Timing and sprite-sequencer PROMs, LS74/gate nets with board-position names, ping-pong 6148 line buffers, bus-request audio. |

Lean distribution: -2: 11, -1: 4, 0: 2, +1: 8, +2: 15.

## Errors and invalid outputs

None. Every source fetch succeeded on the first try, and all 40 outputs passed the check on the first run: the JSON parses, has every field in the rubric's Output section, has `lean` in −2..+2, and cites in `where` only files from the core's build-file list. No core was rerun and no output carries an `invalid` field.

One setup note: `mame_commit` in `batch1.json` holds the hash followed by a newline and two comment lines. Only the first line, `78e14fa58b32f4236ae091865dcc55c4b793d05d`, was used for the MAME checkout.

## Rubric ambiguities reviewers ran into

No reviewer recorded an ambiguity inside its JSON. The quotes below come from the reviewers' final reports to the session.

### Files the core uses that are not in its build-file list, or listed files that are never instantiated

- **jtgunsmk**: "One gap: the top-level video module, `jt1943_video`, is not in the list of files the build compiles. I didn't open it, so the colour mixer and the priority PROM logic were not reviewed. That gap is why confidence is medium rather than high."
- **jttoki**: "`jttoki_main.v` instantiates a `jttoki_video_mmr` module (the scroll registers) that is not in the compiled file list, so I could not review how the scroll registers are decoded."
- **Druaga**: "`rtl/ioctrl.v` pulls in `rtl/ioctrl_0.v`, `rtl/ioctrl_1.v` and `rtl/ioctrl_2.v` with `` `include ``. They were not in the allowed file list, so I didn't open them, and the I/O-chip finding rests on `ioctrl.v` alone."
- **jtlabrun**: "The labrun build does not instantiate the compiled contra files `jtcontra_main`, `jtcontra_video`, `jtcontra_colmix` and `jtcontra_007452`, so I only skimmed them."
- **Tutankham**: "The other custom-chip files (k083, k501–k503, k526, k528) are compiled but never instanced, so I left them out."
- **jtexed**: "`jtgng_video` isn't instantiated by this core's video module, and the Exed Exes scroll layers use their own `jtexed_scr1`/`jtexed_scr2` modules."

### MAME counterpart not in the core's MAME file list

- **Arcade-BlackWidow_(derpyder)**: "MAME's own AVG device source was not in the provided file list, so I could not compare the AVG's scale and intensity logic directly. The only MAME link for the intensity line is a code comment, so I did not count it."
- **jttoki**: "The MAME device file for the sound interface (seibusound.cpp) was also not provided. Because of that, I cited the sound findings against the address maps in `toki.cpp` and `cabal.cpp` rather than against the device's own code."
- **Druaga**: "The sound generator (`rtl/wsg.v`) was not scored because no matching MAME sound source was provided."

### One module per custom chip, when MAME also has one device class per chip

- **SegaXBoard**: "there is one module per custom chip, but each matches a MAME device class with the same register interface, so it doesn't separate the two."
- **Arcade-NamcoS2_STD**: "there is one module per custom chip, but the split follows MAME's device files one to one, and the ports are a start/busy/line-buffer interface rather than chip pins."
- **TaitoAir_1.0_(retrogarage)**: "The only hardware-side evidence is weak: the TC0140SYT and the TC0080VCO RAM have their own modules, but MAME also has device classes for those chips."
- **Darius**: "The PC060HA sound-communication chip is its own module with pointer registers and a nibble-wide shared RAM. MAME also models it as a separate device, so this says little."

### Board logic that MAME itself documents

- **Escape**: "The GAL equations (FORCEMC0, PF/M, SHADE, M7) are written as literal sum-of-products with the board's net names. This is weakened because those equations come from the MAME driver."
- **CanyonBomber**: "The noise generator's taps match MAME's, but both just describe the board's shift registers, so that finding is neutral."

### Generic FPGA or framework structure that matches neither side

- **jtcomsc**: "the per-line tile and sprite engines writing into line buffers are standard FPGA practice and match neither MAME's draw order nor the chip's own fetch timing."
- **jttoki**: "Each layer is a thin wrapper around a generic jtframe engine (tilemap, scroll, objdraw, vtimer). That is framework structure, not a split along the board's custom chips, so I counted it as neutral."
- **Arcade-Gyruss_(MrX-8B)**: "Modules are split by CPU or subsystem (main, sub, video, sound), not one per chip, and signal names are the author's own (BGVA, SPAA, SPHT), not the board's net names." The video findings still lean hardware, so the overall lean is 0.
- **jtflane**: "below the chip level the logic is generic behavioural Verilog, not board-level gates or counters", so the lean stops at +1.

### Code paths that switch between MAME behaviour and board behaviour

- **Vindicators**: "Optional switches that reproduce MAME's behaviour (`DAC_MAME_COMPAT`, `MAME_MAILBOX`) are off by default. With them off, the sound-board link sends each byte as a serial frame." The reviewer counted these as neutral.
- **Arcade-KonamiGX_(ppriest)**: "the `GX_ORDER` and `GX_DMA_ALWAYS` settings turn off its priority-sorted DMA and its DMA-enable bit, so it behaves like MAME's live, RAM-order sprite draw."

### A process deviation a reviewer reported

- **Arcade-KonamiGX_(ppriest)**: "One grep accidentally searched outside the allowed files and printed lines from the repo's `sim/` and `sys/` folders. I did not use that output for any finding, and those files are not in `files_read`." The stray lines came from the core's own checkout under `/tmp/src`, not from this repository.
