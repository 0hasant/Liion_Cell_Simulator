# Quilter notes: what it can and can't do for this board

Quilter (app.quilter.ai) does placement and routing for the cell test bench PCB. Claude's role is the controller: prepare the input, set the constraints, review the candidates against `docs/LAYOUT_REVIEW.md`, ask for revisions, and pick the candidate to keep.

Last updated: 2026-10-28

## 1. Quilter can't do these (work around them ourselves)

| Limit | What it means for us | Workaround |
|---|---|---|
| **No single-sided boards.** Lowest stackup offered is 2 layers (CircuitHub, JLCPCB, MacroFab and Sierra presets only). | Every candidate uses top and bottom copper. | Mill both sides on the Snapmaker with alignment pins and wire every via, or hand-convert top tracks to wire jumpers in KiCad. Score candidates on top-track count and via count (`LAYOUT_REVIEW.md` section F). |
| **No per-net layer restriction** ("route this net on bottom only"). The only custom constraints are Preserved Pours, Net Widths by Layer, Custom Component Proximity. | Can't force a one-sided result. | Same as above. Net Widths by Layer can make top-layer widths impractical, but that is untested. |
| **No custom stackup.** Only fab presets. | Copper weight is 1 oz in the JLCPCB 2-layer preset. Widths are computed for 1 oz (conservative for 2 oz). | Edit the fabricator minimums instead (done: 0.5 mm track, 0.4 mm clearance, 1.8/0.9 mm via, 1 mm edge). |
| **Recommends designs of 10 A or less;** high current should use pours. | Our cell path is 10 A (trip 11 A). | Cell path, GND, VIN and CHG_OUT set as power nets with "Attempt power pour". Check copper width by hand (`LAYOUT_REVIEW.md` section A). |
| **No schematic checking.** Quilter implements the netlist, it doesn't proofread it. | Schematic mistakes go straight into the layout. | Schematic review stays with us (ERC, datasheet pinouts, module pin orders). |
| **Can't tell connectors from other parts.** | Unplaced connectors would end up in the middle of the board. | All connectors (J*), mounting holes (H*) and the IRFP260N (Q301) are pre-placed and locked in the input file. |
| **Leftover vias block placement** (it assumes they are intentional). | Old copper must be removed. | Input board has no tracks, vias or zones (`hardware/quilter_input/`). |
| **No silkscreen cleanup.** | Reference designators may overlap pads or each other. | Fix silkscreen in KiCad after download. |
| **No "star point" or ground-split constraint.** Only one Primary Ground, and region pours need placement regions. | It can't enforce that the 10 A return and the analog ground meet at one point. | Review by hand (`LAYOUT_REVIEW.md` section B). The real fix is a separate power-ground net in the schematic (open item). |
| **Impedance pairs need 4+ layers;** a pair on 2 layers is avoided. | It auto-flagged ADC_VP/ADC_VN as a 100 ohm pair. | Removed. These are DC Kelvin lines; review them as a pair by hand. |
| **No formal revision request on a candidate.** | We can't say "move R307 closer to Q301" on a finished candidate. | Revise by: (1) downloading the best candidate, locking the good parts in KiCad, unplacing the bad area and re-uploading as a new job; or (2) duplicating the job with changed constraints (Custom Component Proximity, power-net currents, floorplan regions). |
| **New jobs in a project must stay within ~10 %** of the pin count, component count, footprints and BOM. | Big schematic changes (e.g. splitting GND) may need a new project. | Fine for constraint-only revisions. |
| **Browser upload only;** no API or connector. | Claude drives it through the built-in browser. | Input files are fetched from this public repo (`raw.githubusercontent.com/.../hardware/quilter_input/`) and dropped into the upload box by script. Push inputs before starting a job. |
| **Job time 1 to 10 hours.** | Results aren't immediate. | Quilter emails when done; Claude also schedules a check. |

Outputs come back in the same format we uploaded (KiCad). A candidate counts as successful only at 100 % routing, zero DRC errors, and passing physics checks (PRCs, e.g. "overheated length" on high-current nets, with a 20 degC rise limit).

## 2. Settings used for job "v0.3 CNC 2-layer, 0.5/0.4mm, 11A cell path" (2026-10-28)

- **Job:** https://app.quilter.ai/jobs/6ae20c36d2060d651ad21e0f (project "Cell Test Bench")
- **Input:** `hardware/quilter_input/` (11 files). Board 180 x 130 mm; 27 parts locked (all J*, H101-H104, Q301); 106 parts for Quilter to place.
- **Stackup:** JLCPCB 2-Layer 10 mil / 6 mil, 1 oz.
- **Fabricator minimums (edited for CNC):** trace 0.5 mm, clearance 0.4 mm, via 1.8 mm pad / 0.9 mm hole, board margin 1 mm.
- **Floorplan:** prefer single-sided placement (all parts on top), component clearance 1.3 mm (Quilter's suggestion), no regions.
- **Power nets:**

| Net | Current | Pour |
|---|---|---|
| CELL_P_RAW, CELL_P, CELL_N, LOAD_P, LOAD_D, GND | 11 A | yes |
| VIN, /Power/VIN_RAW | 10 A | yes |
| CHG_OUT | 6.5 A | yes |
| +12V, +12V_SW, TEC_A, TEC_B | 4 A | no |
| +5V | 1 A | no |
| +3V3, BP_5V, VREF nets | 0.5 A | no |

- **Removed:** ADC_VP/ADC_VN differential pair; V_FAST and a duplicate VIN (auto-detected as power nets).
- **Bypass caps:** 18 auto-detected pairs kept.

## 3. Ideas for the next job (if the first candidates need it)

- Custom Component Proximity: R307 to Q301 gate; U301 to Q301; R201 to J205; D201/D202 to K1/K2; C304/C305 to U301; R501-R505 + C501/C502 to U501.
- Floorplan regions: power corner (J205, F202, K1, K2, R201, Q301, J301, J401) vs analog block (U301, U501, U502, U302, U401, U601-U603) vs MCU/thermal (J801/J802, J701/J702, Q702).
- BTS7960 decided: option (a) (PROJECT_SYNC section 7). Before the next job, remove J703 and the J702 M+/M- pins (TEC_A/TEC_B) from the schematic, regenerate `hardware/quilter_input/`, and drop TEC_A/TEC_B from the power-net list.

## 4. Results of the v0.3 job (finished 2026-10-28 21:37, 3 h 26 min)

No candidate reached 100 % routing, so none is "successful" in Quilter's terms.

| Candidate | Routed | Vias | Quilter DRC items | Parts |
|---|---|---|---|---|
| 1.1 | 92.3 % | 111 | 16 | all on top |
| 2.1 | 91.3 % | 161 | 21 | all on top |
| 3.1 | 92.0 % | 146 | 15 | all on top |
| 4.1 | 90.9 % | 110 | 19 | both sides |
| 5.1 | 89.9 % | 104 | 18 | both sides |
| 6.1 | 93.7 % | 133 | 14 | both sides |

- **Unrouted nets** in every candidate are mostly analog ones around R201/U301: ISNS_G, ISNS_N, GND, I_MON, MON_RAW/MN or OA_OUT/SETP/MB, ADC_IN, plus a few control lines (TEC_EN/PWM, K1_EN, SDA).
- **"Prefer single-sided" is only a preference:** candidates 4-6 still put parts on the bottom.
- **Via count is far too high for CNC** (104-161 wire vias).
- **DRC items are mostly our own settings:**
  - Setting the via hole minimum to 0.9 mm also flags every 0.8 mm component hole.
  - Quilter's 0.4836 mm tracks are just under the 0.5 mm minimum.
- **Real CNC problem found:** the K1/K2 relay coil pads (A1/A2) are **2.1 x 0.5 mm slots** (for flat blade pins). A 0.5 mm-wide slot needs a 0.5 mm end mill; a normal drill can't make it. Check the ALFG2PF121 pin size and change them to round holes (or wider slots) that the Snapmaker can drill.

### Changes for the next job

1. Use the new input (J703 and TEC_A/TEC_B removed).
2. Take GND off the 11 A power-net list; keep the cell-path nets.
3. Set the minimum hole to 0.8 mm (via hole stays 0.9 mm in practice), minimum trace 0.48 mm.
4. Add Custom Component Proximity for U301/R201/R307/Q301 and the ADS1115 filters, and floorplan regions (power corner, analog block, MCU/thermal).
5. Fix the relay coil pads in the footprint first (round holes the CNC can drill).
