| case | category | lenient | v1_current | v2_any_latin | v3_lenient_explicit | v4 |
|---|---|---|---|---|---|---|
| `pos_adjacent` | english_word | pos | 0.060 | 0.205 | 0.886* | 0.811* |
| `pos_spaced` | english_word | pos | 0.040 | 0.438 | 0.769* | 0.706* |
| `pos_sentence` | english_sentence | pos | 0.927* | 0.872* | 0.920* | 0.920* |
| `pos_phrase` | english_phrase | pos | 0.807* | 0.861* | 0.947* | 0.921* |
| `pos_noun` | english_word | pos | 0.433 | 0.611* | 0.465 | 0.222 |
| `pos_long_eng` | english_sentence | pos | 0.611* | 0.909* | 0.658* | 0.895* |
| `pos_greeting` | english_phrase | pos | 0.958* | 0.949* | 0.967* | 0.955* |
| `neg_katakana` | katakana | neg | 0.047 | 0.026 | 0.033 | 0.045 |
| `neg_katakana2` | katakana | neg | 0.039 | 0.021 | 0.026 | 0.037 |
| `neg_katakana3` | katakana | neg | 0.028 | 0.020 | 0.030 | 0.090 |
| `neg_brand_iphone` | brand | neg | 0.037 | 0.211 | 0.028 | 0.030 |
| `neg_brand_youtube` | brand | neg | 0.041 | 0.372 | 0.030 | 0.032 |
| `neg_brand_multi` | brand | neg | 0.034 | 0.058 | 0.030 | 0.037 |
| `neg_char_latin_name` | proper_noun | neg | 0.279 | 0.733* | 0.441 | 0.050 |
| `neg_char_latin_name_sp` | proper_noun | neg | 0.389 | 0.930* | 0.452 | 0.331 |
| `neg_url` | url | neg | 0.073 | 0.489 | 0.045 | 0.037 |
| `neg_version` | alnum | neg | 0.046 | 0.056 | 0.040 | 0.024 |
| `neg_number_unit` | alnum | neg | 0.041 | 0.487 | 0.036 | 0.025 |
| `neg_acronym` | acronym | neg | 0.056 | 0.153 | 0.390 | 0.039 |
| `neg_code` | code | neg | 0.572* | 0.785* | 0.636* | 0.151 |
| `neg_ok` | acronym | neg | 0.732* | 0.730* | 0.858* | 0.243 |
| `org_english_role_noun` | organic | pos | 0.615* | 0.392 | 0.873* | 0.818* |
| `neu_pure_ja` | control_negative | neg | 0.025 | 0.021 | 0.026 | 0.043 |

(* = flagged, 閾値0.5 / v4 = candidates/v4_production.txt)
