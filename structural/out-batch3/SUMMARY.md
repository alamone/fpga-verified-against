# Structural review, batch 3: summary

90 cores from `structural/batch3.json`, each reviewed by an independent subagent against `structural/rubric.md` at its pinned commit, compared with MAME at `78e14fa58b32f4236ae091865dcc55c4b793d05d`. Lean runs from -2 (clearly MAME-structured) to +2 (clearly hardware-structured). The full findings are in `structural/out-batch3/<id>.json`; the one-line summaries below are condensed from each reviewer's summary.

| id | lean | confidence | comment_dependence | findings | summary |
|---|---|---|---|---|---|
| Sprint1 | +2 | high | some | 12 | TTL netlist of the board: sync PROM, 74LS166 playfield, per-car 74163/74165 motion logic, 74LS279 collision latches. |
| CrystalCastles | +2 | high | some | 11 | Board-block modules (sync chain, motion-object control, line-buffer pair) on raster counters; only the vscroll clamp echoes MAME. |
| CrazyClimber | +1 | medium | some | 12 | Raster-driven pipeline with hblank sprite line buffer and counter-driven big sprite; one flat module, no board names. |
| Jackal | +2 | high | some | 12 | Board-level top with parts by reference designator; 007343 PAL as sum-of-products, 007327 palette chip, 005885 scan pipeline. |
| KickAndRun | -1 | medium | some | 11 | Board-flavoured CPU glue, but the sprite/tile renderer walks MAME's screen_update_kicknrun loop and constants. |
| Finalizer | +2 | high | some | 13 | 005885 custom-chip module with chip pins as ports; per-pixel tile pipeline, per-line sprites, counter-bit interrupts. |
| jtbubl | +2 | high | some | 12 | Per-scanline object scanner over four VRAM chips with the a71-25 PROM driving control; CPU contention MAME lacks. |
| TurkeyShoot | +2 | high | some | 11 | IC60 decoder PROM into six 4-bit VRAM chips, slot-by-slot blitter via HALT/BA/BS, delay-line fine scroll. |
| RiverPatrol | +1 | medium | some | 12 | Raster-driven Crazy Climber-family pipeline with hblank sprite line buffer and address-XOR flips; one flat module. |
| MrDo | +2 | high | some | 11 | Cascaded ttl161 counters, per-line sprite search into a 15-deep stack, J10 timing PROM, board-location names. |
| NaughtyBoy | 0 | low | none | 6 | Not judged: the batch file list omits the files holding the board logic; placeholder lean 0. |
| ffbiomtoy | -2 | high | none | 11 | Gaelco renderer rebuilt from MAME: priority rank() mirrors screen_update draw calls, sprite loop and decrypt copied. |
| Zaxxon | +1 | medium | some | 11 | Video built like the board (per-line sprite search, online RAM, line buffer); sound is a MAME-style sample player. |
| ffdestroyer | -1 | medium | none | 12 | CDP1869 video modelled as MAME does: charram addressing, PCB-bit side effect and pen-index palette copied from MAME. |
| Xevious | +1 | medium | some | 12 | Board-style sound sequencer and scan-time tile/sprite pipelines; 06XX I/O chip is a near-copy of MAME's namco06. |
| CrazyKong | +1 | medium | none | 11 | Raster-driven pipeline, A5-dropped colour RAM, hblank sprite line buffer; flat module, several features missing. |
| Superman_(diegov-au) | -2 | medium | none | 11 | tc0140syt is a port of MAME's device and x1_001 walks MAME's draw loops; generic video timing. |
| Berzerk | +1 | medium | some | 12 | Video and CPU glue follow the board; sound noise generator and 6840 model match MAME's exidysound. |
| Breakout | +2 | high | none | 10 | Gate-level TTL copy with chips by board position and datasheet pin names; MAME's own netlist is the shared source. |
| BankPanic | +2 | high | some | 11 | Netlist-style core: 74161 raster chains, Sega PALs as gate equations, 74138/139 decode, latch-pipelined tiles. |
| TropicalAngel | +1 | medium | some | 10 | Raster-driven video pipeline and pin-wired sound board; background scroll rules match MAME's draw_background. |
| MCR2 | +2 | high | some | 11 | SSIO counters and PROM-clocked volume counters as real hardware; per-line sprite scan into swapping line buffers. |
| Pengo | +2 | high | some | 12 | MikeJ-style board model: preset raster counters, hcnt-gated VRAM sharing, adder sprite match, serial-adder sound. |
| Popeye | +1 | medium | some | 12 | Scan-time char/background/sprite blocks with line buffers and loaded counters; protection transliterated from MAME. |
| Asteroids | 0 | medium | some | 13 | Split: PROM-driven DVG and board counters vs. MAME-copied input reads and node-by-node MAME discrete sound. |
| NinjaKun | +1 | low | some | 10 | Per-pixel tile fetch and per-line sprites, but MAME's 240 Hz IRQ, layer order and per-game HWTYPE structure. |
| ZigZag | +2 | high | some | 11 | Galaxian netlist style: 74138/139 decode, 9N addressable latch, part-named sprite pipeline, parallel SPRITE2 copy. |
| Dominos | +2 | high | some | 11 | Netlist with chip-designator names: PROM address decode, sync PROM chain, 74LS166 playfield, selector inputs. |
| VBall | -1 | medium | none | 12 | No chip modules; MAME handler names, background_scan mapper and spritelayout formula; per-pixel PROM palette. |
| Psychic5 | +2 | high | some | 11 | CPU and video boards with a module per hybrid chip; BUSRQ sprite copy, PROM-sequenced counters, adder blender. |
| RshnAtk | -1 | medium | some | 11 | No 005849 module; IRQGEN, sprite bank polarity and sprite loop follow MAME's k005849 and draw_sprites. |
| SpaceInvaders | +1 | medium | some | 12 | Chip-named 74161-style counters, gate-level interrupt and shared-RAM wait logic; MAME tables and samples for sound. |
| Jailbreak | +2 | high | some | 11 | One instance per physical chip; 005849 module with chip pins; raster-counter video and board-style glue logic. |
| jtsf | +1 | medium | some | 11 | Shared GnG modules give board-like sprite DMA and line buffers; SF-specific glue is thin, a few MAME-form details. |
| Syvalion_(diegov-au) | -2 | high | none | 12 | tc0080vco zoom and sprite math use MAME's expressions and loops; tc0140syt copies taitosnd.cpp. |
| MCR3 | +2 | high | some | 12 | Board-rate raster timebase, per-line sprite machine with staging RAM, SSIO counters and PROM volume logic. |
| jtsectnz | +2 | high | some | 11 | Shared GnG pipeline: BUSRQ sprite DMA, per-line object buffer, counter-chain draw timing, gate-logic scroll. |
| BlackWidow | +1 | medium | some | 11 | AVG run from the real state PROM with latch/strobe decode, 2 KB block decode with mirrors; MAME AVG not compared. |
| Tempest | +2 | high | some | 12 | Math box runs the original microcode on an Am2901 model; AVG driven by the state PROM; MAME's go_w is C algorithms. |
| Arcade-Kikikaikai_(alpuy) | -2 | high | some | 12 | Sprite engine runs MAME's screen_update_kikikai per scanline; gfx decode, palette, MCU glue from MAME. |
| jttrojan | +2 | medium | some | 12 | GnG/1943 family pipeline with BUSRQ sprite DMA, per-line sprite search and priority-PROM-shaped mixer. |
| vimana_(va7deo) | -1 | medium | some | 11 | One big always block replicating MAME's draw order, offsets and sprite decode; CRTC timing and DAC table board-like. |
| BurningRubber | +2 | high | some | 12 | One raster-scan pipeline: hblank sprite latch, clear-on-read line buffer, per-pixel priority, address-rewired mirror RAM. |
| ffbigkarnk | -2 | high | none | 12 | Gaelco video rebuilt from MAME: pcode/rank priority passes, pri_mask table, force-high rule, draw_sprites loop. |
| Subs | +2 | high | some | 11 | 74163/74165 motion objects, 74LS166 playfield, gate-level mixer and sync, 74LS251/253 input multiplexers. |
| DigDug | -1 | medium | some | 11 | Per-pixel layers, but tile/sprite formulas copied from MAME and custom I/O chips folded into one behavioural model. |
| RingKing | -1 | medium | some | 11 | Flat core.v: background layout, sprite draw order, HOLD_LINE IRQ and sound NMI follow MAME; 74LS138-style decode. |
| StarCastle | +1 | medium | some | 12 | PROCEED window, E8 timing table and board-quirk CCPU behaviours; CPU is an opcode interpreter, laser VCO from MAME. |
| Inferno | +2 | high | some | 12 | Williams-2 board model: decoder PROM into nibble RAMs, phase-slotted blitter, delay-line scroll, raster PIA inputs. |
| Gaplus | -1 | medium | some | 12 | Per-line sprite work RAM and per-pixel mixing; custom I/O chips, explosion samples and starfield control from MAME. |
| SolomonsKey | 0 | medium | none | 11 | Scan-time tile fetch and per-line sprites, but protection, sound IRQ rate and clocks follow MAME. |
| ffblswhstl | +1 | medium | none | 12 | K052109 scan-time fetch and K053251 per-pixel mixer vs. MAME-derived K054000, sprite DMA sort and zoom table. |
| MajorHavoc | +1 | medium | some | 12 | State-PROM AVG with separate clock domain and unemulated features; IRQ counters and comm flags copy MAME. |
| Ultratank | +2 | high | some | 10 | Counter/shift-register motion objects, per-pixel collision latches, 74154/9321/9334 decode, sync PROM chain. |
| MCR1 | +2 | high | some | 11 | Raster-addressed tiles, per-line sprite machine with staging copy, SSIO counter chain and PROM volume counters. |
| TimePilot | +2 | high | some | 11 | One module per Konami custom chip and PLA with pin-named ports; 526/528 PLAs as sum-of-products; one MAME timer table. |
| TaitoSJ | +2 | high | some | 11 | Per-pixel priority PROM, 74LS166 layer shifters, hit latches, TTL MCU glue with the 68INTAK flop MAME omits. |
| ffkonamigt | +2 | high | none | 12 | Module per Konami chip (K005289-K005295), board-position decoders, flip-flop interrupts, accumulator zoom. |
| prehisle_(va7deo) | -1 | medium | none | 10 | Layer mixing copies MAME's draw order; video split mirrors MAME's tilemaps plus draw_sprites; map-style decode. |
| jtcastle | +2 | medium | some | 11 | Per-pixel priority PROM MAME marks unused, one module per 007121 chip with in-chip colour PROMs, per-line sprites. |
| Tecmo | 0 | medium | some | 10 | Clean behavioural re-implementation: pixel-clock tile pipelines, but frame-buffer sprites and MAME-style priority. |
| Scramble | +2 | high | some | 13 | One H/V counter pair drives everything; 74138-style decode, shift-register video, loadable shell counters. |
| SilverLand | +1 | medium | none | 12 | Crazy Climber-family raster pipeline: phase-slotted fetch, hblank sprite line buffer, counter-indexed big sprite. |
| ffaltair | -2 | medium | none | 12 | CDP1869/1870 rebuilt the way MAME emulates it: charram addressing, PCB bit, row/colour/palette formulas from MAME. |
| Exerion | +2 | high | some | 11 | Board-chip netlist with board-position names; scan-time sprites with swapping line buffers; 1-of-13 latch decoder. |
| CosmicGuerilla | -1 | medium | some | 11 | Output/input decode copies MAME's cosmicg handlers; MAME samples and ROM patch; no MC6845 model. |
| CrazyBalloon | +1 | low | some | 11 | Raster-compared sprite/collision and 555-based audio, but PC3092/PC3259 flattened into MAME-style handlers. |
| DottoriKun | +2 | high | some | 10 | Gate-and-counter netlist: cascaded 4-bit counters, LS166-style shifter, gated Z80 clock, IC-named signals. |
| jtgaiden | -1 | medium | none | 11 | Mixer, palette layout and protection MCU transliterate MAME's tecmo_mix and protection_w; generic JTFRAME parts. |
| jtmikie | +1 | medium | some | 12 | Shared jtkicker modules: per-line sprite rescans, PROM-addressed colour mixer, board-style sound decode. |
| ffsquash | -2 | high | none | 11 | Gaelco renderer from MAME: rank() mirrors screen_update_squash, sprite loop, decrypt and tile decode copied. |
| IremM107 | +2 | high | some | 12 | One module per Irem GA chip, V33 bus-status decode, DMA engine MAME lacks, scan-time rendering, PAL-style palette select. |
| demonwld_(va7deo) | -1 | medium | some | 11 | Draw order, offsets, scroll math and sprite decode match MAME; CRTC-driven timing and resistor DAC board-like. |
| ReliefPitcher | +1 | medium | some | 12 | GAL modules with pin vectors and 74163 DTACK counter vs. VAD registers and sprite walker following atarivad/atarimo. |
| jtcontra | +1 | medium | some | 10 | One module per chip (007121 twice, 007766, 007452), per-pixel mixing, raster-counter interrupts; behavioural internals. |
| jtsbaskt | +1 | medium | some | 11 | PROM-chain colour path, scan-paced tiles, per-line sprite table; shared kicker modules keep it from +2. |
| Galivan | -1 | medium | none | 12 | Generic line-drawing state machines; priority, sprite decode, colour banks and constants match MAME's handlers. |
| Starforce | +2 | high | none | 12 | TTL-level netlist of the three-board PCB: board modules on a backplane, gate-level 74xx models, priority encoder. |
| CongoBongo | +1 | medium | some | 11 | Raster-timed video with per-line sprite search; sprite DMA algorithm and WAV sound effects follow MAME. |
| TraverseUSA | +2 | medium | some | 12 | Raster-driven video with per-line sprite scanner and swapping line buffers; one MAME transmask hack. |
| Pooyan | +1 | medium | some | 11 | Raster counters, scan-time tile fetch, per-line sprite buffers, LS90-style sound timer; one flat video module. |
| Performan | +2 | high | some | 11 | Netlist of the board: decoder-chip modules, LS299 shifters, PROM-sequenced sprite timing into 6148 line buffers. |
| PolyPlay | +1 | medium | some | 11 | Pixel-pipeline video with bitplanes wired to RGB and pin-level CTC/PIO wiring; board logic thin and generic. |
| jtnarc | +1 | medium | none | 12 | TMS34010 screen-refresh and VRAM row-transfer cycles drive display and auto-erase; DMA blitter differs from MAME. |
| Robotron | +2 | high | some | 11 | Decoder PROMs, single raster counter, SC1 blitter on the bus with nibble write enables; Blaster additions follow MAME. |
| MysticMarathon | +2 | high | some | 11 | Williams-2 board model: HALT/BA/BS bus sharing, IC60 PROM into six VRAM chips, scan-time shifters, DMA blitter. |
| Sprint2 | +2 | high | some | 12 | TTL netlist: per-car 74163/74165 motion logic, 74LS279 collision latches, decoder PROM and 9334 latch. |
| SEGASYS1 | -1 | medium | none | 11 | Sprite engine, mixer index and collision registers follow MAME's draw_sprites; generic timing, no VRAM waits. |
| PsikyoSH2 | +1 | medium | none | 10 | One module per chip wired by chip-select/WAIT_N/IRQ lines, raster-slot background reads; FPGA-style internals. |
| SegaSys1+2_(TheJesusFish) | -1 | low | none | 11 | Sprite render states follow MAME's draw_sprites loop and offsets; board-like BG scan, missing VRAM waits. |

## Errors and invalid outputs

- **Fetch errors:** none. Every core and the MAME sparse checkout fetched on the first try.
- **Invalid outputs:** none. All 90 JSON files passed the check (they parse, have every Output field, lean in -2..+2, and every file cited in `where` is in the core's file list) on the first run, so no core was rerun.
- **NaughtyBoy: incomplete file list.** The entry's `build_files` leave out the files that hold the board's logic (`rtl/naughty_boy.vhd`, `rtl/naughty_boy_video.vhd`, `rtl/naughty_boy_effect1..4.vhd`, `rtl/naughty_boy_noise.vhd`, `rtl/tms3615.vhd`, `rtl/prom_palette_1/2.vhd`), although `Arcade-NaughtyBoy.sv` instantiates `naughty_boy`. The reviewer stayed inside the given list and wrote a placeholder (lean 0, confidence low). The file passes the check, but its verdict is not a reading of the board logic. A rerun with the same list would give the same result, so it was not rerun; it needs a corrected file list. A scan of the other 89 lists found unlisted modules only in the MiSTer framework and PLLs.
- **Setup path fixes (outside the repository, in `/tmp/src`):** for the five `ff*` Gaelco/Konami cores (ffbiomtoy, ffbigkarnk, ffblswhstl, ffkonamigt, ffsquash), `build_files` repeat the `subdir` prefix (`cores/<x>/hdl/...` under `cores/<x>`). A symlink `cores/<x>/cores -> <checkout>/cores` made the listed paths resolve as given. Three listed paths differ from the repository only in case, and were symlinked to the real files: CrystalCastles `rtl/pokey/` -> `rtl/Pokey/`, Exerion `modules/cpu-t80/` -> `modules/cpu-T80/`, TaitoSJ `rtl/Mc68705p3.v` -> `rtl/mc68705p3.v`. All three are shared libraries (POKEY sound chip, T80 CPU, 68705 MCU). The prompts were not changed.

## Rubric ambiguities reviewers ran into

Quoted from reviewers' final reports or JSON.

**MAME device files outside `mame_files`.** Several boards' custom logic is emulated in MAME device files the batch did not list, so reviewers could not check those parts, or checked them from memory:
- Asteroids: "MAME's own vector-generator source was not in the allowed files, and it may split the same way."
- BlackWidow: "MAME's own AVG emulation is not in the allowed file list. MAME may use the same PROM-driven latch/strobe layout, so I couldn't rule out that the AVG structure is shared with it."
- Tempest: "MAME's vector-generator source (`avgdvg.cpp`) wasn't in the allowed file list".
- MajorHavoc: "The MAME vector generator source (`avgdvg.cpp`) was not in the allowed file list ... This is the main reason confidence is medium rather than high."
- ffdestroyer: "My reference to MAME's `cdp1869` device here is from memory; that file was not among the sources provided."
- ffaltair: "MAME's chip emulation source (`cdp1869.cpp` / `cdp1869.h`) was not among the provided files. The geometry, colour, palette and timing comparisons rest on my memory of that code; the JSON marks those refs as "recalled"."
- Superman (diegov-au): "MAME's x1_001 source was not in the supplied files, so this rests on my memory and I gave it less weight."
- Berzerk: "MAME's S14001A source wasn't in the allowed files, so I couldn't check the speech block against it."
- StarCastle: "the MAME CCPU source wasn't in the allowed files, so I couldn't confirm that."
- Pengo: "I did not read `pacman_v.cpp`, where MAME draws its sprites and tiles, because it was not on the allowed list."
- ffblswhstl: "MAME's palette source wasn't among the provided files, so I didn't check them in code."
- SEGASYS1: "I could not compare it with MAME because that code is not in the files provided." (program decryption)

**Rule 4 when MAME's driver is itself a netlist.**
- Breakout: "MAME's nl_breakout.cpp is itself a netlist taken from the same schematic, so the gate wiring is the same on both sides. I scored that as neutral".

**Board-specific CPUs and chip models vs. rule 2's "ignore shared libraries".**
- StarCastle: "The CPU is an opcode-level interpreter: one big case statement over the opcode with per-instruction cycle counts, not the board's TTL datapath." (the CCPU is board logic on this hardware, but rule 2 lists CPU cores as libraries to ignore)
- Berzerk: "The S14001A speech chip is a step-by-step state machine that reads like a translated software emulator. It is a chip model, so I gave it little weight for board structure."

**Shared in-family modules vs. this board's own logic.**
- jtsf: "the code written for Street Fighter itself is thin, mostly address decode and glue. The hardware-shaped structure sits in the shared GnG modules."
- jttrojan: "most of the video pipeline is shared GnG/1943 family modules, not Trojan-specific logic."
- jtsbaskt: "much of the video comes from the shared kicker modules, which pick per-game tile attribute layouts through a LAYOUT parameter. That is reusable abstraction, not this board's netlist".

**Files for sibling games in the compile list.**
- ffbiomtoy: "That function belongs to Squash, a sibling game; MAME runs Biomechanical Toy through `screen_update_maniacsq`."
- ffdestroyer: "`draco_sound.v` ... belongs to the sibling Draco machine, not Destroyer."
- Scramble: "These only apply to sibling games, not Scramble's own path."

**What separates +1 from +2.** Reviewers differed on whether a hardware-style design without chip-level modules or board net names can score +2:
- CrazyKong: "everything sits in one flat module with abstract names, not one module per chip or board net names. ... Neither point suggests MAME, but both weaken the hardware case."
- RiverPatrol: "the design reads as hand-built in hardware style, not a chip-by-chip copy of the schematics."
- TraverseUSA scored +2 (confidence medium) although "All the board logic is in one flat file rather than one module per chip" and "Signal names are descriptive (`hcnt`, `spr_*`), not the board's own net names."
