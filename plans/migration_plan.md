# Migration Plan — Old → New Taxonomy Populate Files

## Status Key
- [ ] not started
- [~] in progress
- [x] done

---

## Taxonomy Mapping (old field → new taxonomy key)
| Old field          | New key      | Example value       |
|--------------------|--------------|---------------------|
| classification     | taxonomy_1   | hardware            |
| type (after screw_)| taxonomy_2/3 | screw / countersunk |
| description_extra  | taxonomy_4   | hex_head, pozidriv, philips |
| color              | taxonomy_5   | black, bright_zinc_plated, stainless_steel |
| size               | taxonomy_6   | m2_diameter         |
| description_main   | taxonomy_7   | 3_mm_length         |

Folder name pattern: `{t1}_{t2}_{t3}_{t4}_{t5}_{t6}_{t7}`
Example: `hardware_screw_countersunk_hex_head_black_m2_diameter_3_mm_length`

Note on drive type naming (from taxonomy comment):
- old `pozidrive_head` → new taxonomy_4 = `pozidriv`
- old `phillips_head`  → new taxonomy_4 = `philips`
- old `hex_head`       → new taxonomy_4 = `hex_head`

Decimal lengths (grub screws): dot replaced with underscore → `2_5_mm_length`

---

## Phase 1 — New populate files (one per screw type/variant)

- [x] `working_oomp_populate_countersunk.py` — hex_head / black (already created, original sizes)
      NOTE: needs two more generate variants added (pozi/zinc, philips/black) or new files
- [x] `working_oomp_populate_countersunk_pozi.py` — pozidriv / bright_zinc_plated
      Sizes: m2[4,5,6,8,10,12,16] m2_5[5,6,8,10,12,16,20] m3[5,6,8,10,12,16,20,25]
             m3_5[8,10,12,16] m4[6,8,10,12,16,20,25,30,40,50,60]
             m5[8,10,12,14,16,20,25,30,35,40,50,60,70,80,100] m6[10,12,16,20,25,30,40,100,120]
- [x] `working_oomp_populate_countersunk_philips.py` — philips / black
      Sizes: m1_4[3,4,5,6,8,10] m1_5[3,4,5,6,8,10] m1_6[3,4,5,6,8,10]
             m2[3,4,5,6,7,8,10,12,14,16,18,20,22,25,30]

- [x] `working_oomp_populate_socket_cap.py` — socket_cap / hex_head / black (already created)
- [x] `working_oomp_populate_socket_cap_low_head.py` — socket_cap_low_head / hex_head / black
      (same sizes as socket_cap)
- [x] `working_oomp_populate_socket_cap_low_head_ultra.py` — socket_cap_low_head_ultra / hex_head / black
      (same sizes as socket_cap)

- [x] `working_oomp_populate_flat_head.py` — flat_head / philips / black
      Sizes: m2[3,4,5,6,8,10,12,14,16,20,22,25] m2_5[3,4,5,6,8,10,12,14,16,20,22,25]
             m3[4,5,6,8,10,12,14,16,18,20,22,25,30] m4[5,6,8,10,12,14,16,18,20,22,25,30,35,40]
             m5[6,8,10,12,14,16,18,20,22,25,30,35,40] m6[6,8,10,12,14,16,18,20,22,25,30,35,40,45,50]

- [x] `working_oomp_populate_button_head.py` — button_head / hex_head / black
      Sizes: m2[3,4,5,6,8,10,12,14,16,20,22,25] m2_5[3,4,5,6,8,10,12,14,16,20,22,25]
             m3[4,5,6,8,10,12,14,16,18,20,22,25,30] m4[5,6,8,10,12,14,16,18,20,22,25,30,35,40]
             m5[6,8,10,12,14,16,18,20,22,25,30,35,40] m6[6,8,10,12,14,16,18,20,22,25,30,35,40,45,50]

- [x] `working_oomp_populate_grub.py` — grub / hex_head / black + stainless_steel
      Sizes: m1_6[2,2.5,3,4,5,8] m2[2,2.5,3,4,5,6,8,10,12,14] m2_5[2,2.5,3,4,5,6,8,10,12,14]
             m3[2,2.5,3,4,5,6,8,10,12,14,16,18,20] m4[3,4,5,6,8,10,12,14,16,18,20]
             m5[3,4,5,6,8,10,12,14,16,18,20,25,30,35] m6[6,8,10,12,14,16,18,20,30,40]
      Decimal lengths → dot replaced with underscore (e.g. 2.5 → 2_5)

- [x] `working_oomp_populate_machine_screw.py` — machine_screw / pozidriv (no colour) + philips / nylon_white
      Pozi sizes: m2[4,6,8,10,12] m3[4,5,6,8,10,12,16,20,25,30,35,40]
                  m3_5[5,8,10,12,16,20,25] m4[5,6,8,10,12,16,20,25,30,35,40,45,50,60,70,80,90,100]
                  m5[6,8,10,12,14,16,20,25,30,35,40,50,60,80,100] m6[8,10,12,16,20,25,30,35,40,100,120]
      Philips/nylon_white: m3[12,16,20,25]

- [x] `working_oomp_populate_self_tapping.py` — self_tapping / philips / black
      Sizes: m1[3,5] m1_2[3,5,8] m1_4[3,5,8,10] m1_7[5,8,10,12,16] m2[5,8,12,16,20] m2_3[5,6,8,10,12,16,20]

- [x] `working_oomp_populate_thread_forming.py` — thread_forming / philips / black
      Sizes: m2_3[6] m2_5[6] m2_6[6]

- [x] `working_oomp_populate_wood.py` — wood / pozidriv / bright_zinc_plated (loop-based only, no specials)
      Sizes: m2[4,5,6,8,10,12,16] m2_5[5,6,8,10,12,16,20] m3[5,6,8,10,12,16,20,25]
             m3_5[8,10,12,16] m4[6,8,10,12,16,20,25,30,40,50,60]
             m5[8,10,12,14,16,20,25,30,35,40,50,60,70,80,100] m6[10,12,16,20,25,30,40,100,120]

---

## Phase 2 — Wire up new files into working_oomp_populate.py

- [x] Import and call each new generate() in working_oomp_populate.py
      (countersunk variants, socket_cap variants, flat_head, button_head, grub, machine_screw,
       self_tapping, thread_forming, wood)

---

## Phase 3 — Tests

- [x] Create `tests/test_folder_names.py`
      - Import all generate() functions
      - Build full folder name from taxonomy fields:
        `{t1}_{t2}_{t3}_{t4}_{t5}_{t6}_{t7}`
      - For countersunk hex_head black: assert generated names match existing folders in parts/
      - For socket_cap hex_head black: same
      - Smoke test: all generate() calls return non-empty lists
      - Smoke test: no duplicate folder names within or across types

- [x] Create `tests/test_generate_structure.py`
      - Check every returned option dict has required keys: taxonomy_3, taxonomy_4, taxonomy_5, taxonomy_6, taxonomy_7
      - Check taxonomy_6 ends with _diameter
      - Check taxonomy_7 ends with _mm_length

**All 70 tests passing ✓**

---

## Notes
- Special one-off screws (corefix, goldscrew, screwtite) deferred to later
- socket_cap variants (low_head, low_head_ultra) use identical size tables as socket_cap
- All generate() functions use **kwargs so callers can override in future
