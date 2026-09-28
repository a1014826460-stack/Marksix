# Prediction Module Future-Generation Rules

This document is generated from the internal rule manifest. It documents candidate semantics only and never contains future draw values.

Unordered number-set modules (mode 9 / 65 / 88 / 116) never use positional rotation: their `content` is a set of 01-49 numbers, so the display order is a per-issue permutation of the same members and the adjacent-period contract is `display order differs` instead of `full ordered signature`.

Wave-label modules (mode 38 双波中特 / mode 143 一波中特) store the candidate as the **wave label** itself
(`蓝波,绿波`, or `["蓝波|03,04,…","绿波|05,06,…"]`), so their `content_parser` must be
`parse_literal_label_content`; `parse_zodiac_content` only recognizes zodiac characters and returns an empty
tuple for wave labels, which made `is_correct` permanently `null` for mode 38 before 2026-09-28.
The special-number wave comes from `res_color` (last value → 红波/蓝波/绿波) with `fixed_data` sign `波色`
as fallback (`predict.categories.size_parity.special_wave_from_row`) and is embedded in the composite outcome
by `public.api._compute_outcome_from_row`.

Half-wave modules (mode 58 绝杀半波 / mode 490 杀两半波) predict the candidate as the **half-wave label**
itself (`蓝双` / `绿单`), so `_compute_outcome_from_row` must also carry the half-wave atom
(`{波色}{单双}` = `蓝双`) next to the wave and parity atoms; without it the `label in outcome` substring
check can never match and `excludes_hit` returns `True` for every row (the whole column was permanently
"对" before 2026-09-28).

Mode 492 三头四尾 is a `PredictionCategory.MIXED` play (`头:` / `尾:` label prefixes), so its hit semantics
follow the repo-wide mixed rule — **any dimension hits** (特码头或特尾任一落入对应候选即命中), implemented by
`predict.mechanisms.three_head_four_tail_hit` and mirrored by
`frontend/lib/prediction-contract.ts::verifyVerdictAgainstCandidates`.

Mode 30 单双各4尾 splits its candidate across two columns: `dan` must hold 4 **single** tails
(`1尾/3尾/5尾/7尾/9尾`, each tail at most once) and `shuang` must hold 4 **double** tails
(`0尾/2尾/4尾/6尾/8尾`). The generator draws every tail from its own group
(`predict.common.selection_group_quotas` / `domains.prediction.candidate_control` group quotas),
so `0尾` can never appear in `dan` and `1尾` can never appear in `shuang`.


Mode 251 家野两肖 stores its正文 in the **`title`** column (`家禽|牛,马,羊,鸡,狗,猪` = group|members)
and its candidates in **`xiao`**, whose supplier width is **always 2** (两肖, e.g. `蛇,龙`).
The candidate width must therefore come from the `xiao` column; `parse_pipe_label_content(title)`
splits the **group members** on commas and yields 6, which generated `xiao` with 6 zodiacs per issue
(all webs/types, 200+ rows) and made the renderer print `家禽+6肖`. Fixed on 2026-09-28:
`_classify_second_stage_config` infers the width with `_infer_group_widths(..., ("xiao",))`
(`label_count = 2`, same as mode 142 「家野2肖（家野选1，生肖选2）」). Already persisted rows are
**not** rewritten; the compat route takes the width-2 semantic prefix instead.

| mode_id | key | title | rule | outcome semantics | assurance | future control | uniqueness |
|---:|---|---|---|---|---|---|---|
| 3 | rcca | 肉菜草肖 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 5 | title_5 | 天地生肖（天地选1，生肖选2） | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 8 | hllx | 红蓝绿肖（3选2） | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 12 | 3tou | 3头中特 | head | special number head is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 14 | title_14 | 家禽野兽 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 15 | title_15 | 单双公式 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 20 | juesha1wei | 绝杀一尾 | tail_exclusion | special number tail is absent from every candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 26 | qinqi | 琴棋书画 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 28 | danshuangtema | 单双中特（单双码） | parity | special number parity is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature; adjacent 3 periods: display value differs |
| 30 | title_30 | 单双各4尾 | tail | special number tail is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 31 | danshuang4xiao | 单双四肖 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 2; adjacent: full ordered signature |
| 34 | ma24 | 24码 | number | special number is in any candidate | controlled_future | supported | cross-site prefix: 3; adjacent: full ordered signature |
| 38 | shuangbo | 双波中特 | wave | special number wave is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 42 | juesha3xiao | 绝杀3肖 | zodiac_exclusion | special zodiac is absent from every candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 43 | pt2xiao | 平特2肖 | zodiac_flat | any drawn number's zodiac is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 44 | 7xiao7ma | 7肖7码 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 2; adjacent: full ordered signature |
| 45 | heibai3xiao | 黑白各3肖 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 2; adjacent: full ordered signature |
| 46 | 6xzt | 6肖中特 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 2; adjacent: full ordered signature |
| 47 | title_47 | 4肖中特 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 48 | title_48 | 8肖中特 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 2; adjacent: full ordered signature |
| 49 | 9xzt | 9肖中特 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 3; adjacent: full ordered signature |
| 50 | yijuzhenyan | 一句真言 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 51 | 4xiao8ma | 4肖8码 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 52 | sizixuanji | 四字玄机 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature; adjacent 5 periods: display value differs |
| 53 | 3hang | 3行中特 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 54 | pt1wei | 平特1尾 | tail_flat | any drawn number's tail is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 56 | pt1xiao | 平特1肖 | zodiac_flat | any drawn number's zodiac is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 57 | daxiao | 大小中特 | size | special number size is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature; adjacent 3 periods: display value differs |
| 58 | jueshabanbo | 绝杀半波（1个半波） | half_wave_exclusion | special half-wave is absent from every candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 59 | dujiayoumo | 独家幽默 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 60 | 9xiao12ma | 9肖12码 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 3; adjacent: full ordered signature |
| 61 | siji3 | 四季生肖（4选3） | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 62 | yqjs | 欲钱解特 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature; adjacent 5 periods: display value differs |
| 66 | title_66 | 5尾中特 | tail | special number tail is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 69 | 3zxt | 3肖中特 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 72 | sanxiao15ma | 三肖15码中特 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 74 | title_74 | 必中7尾 | tail | special number tail is in any candidate | controlled_future | supported | cross-site prefix: 2; adjacent: full ordered signature |
| 77 | shisi_mazhong | 14码中特 | number | special number is in any candidate | controlled_future | supported | cross-site prefix: 2; adjacent: full ordered signature |
| 78 | sixiao_sima | 四肖四码 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 81 | shiwu_mazhong | 15码中特 | tail | special number tail is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 108 | dxztt1 | 大小中特带1头 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature; adjacent 3 periods: display value differs |
| 117 | sanxiao_siwei_xiao | 三肖四尾 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 123 | sanxiao_siwei_wei | 四尾八码 | tail | special number tail is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 132 | title_132 | 合数单双 | combined_parity | special digit-sum parity is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 143 | title_143 | 一波中特 | wave | special number wave is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 197 | title_197 | 三期4肖 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 198 | title_198 | 逢买必中 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 219 | qianhou_texiao | 前后特肖 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 279 | title_279 | 合数大小 | combined_size | special digit-sum size is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 470 | pt3xiao | 平特3肖 | zodiac_flat | any drawn number's zodiac is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 471 | liangtouzxt | 两头中特 | head | special number head is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 472 | juesha1xiao | 绝杀1肖 | zodiac_exclusion | special zodiac is absent from every candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 473 | juesha2xiao | 绝杀2肖 | zodiac_exclusion | special zodiac is absent from every candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 474 | sxztu | 四不像中特图 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 475 | brainteaser | 脑筋急转弯 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 476 | pmtj_image | 跑马图解（带图） | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 478 | tw_pmt_image | 台湾跑马图（带图） | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 479 | siduanzhongte | 四段中特 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 480 | xiongjiliuxiao | 凶吉六肖 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 481 | wensha10ma | 稳杀10码 | number_exclusion | special number is absent from every candidate | controlled_future | supported | cross-site prefix: 2; adjacent: full ordered signature |
| 482 | sihangzhongte | 四行中特 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
| 483 | sitouzhongte | 四头中特 | head | special number head is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 484 | liuxiao18ma | 六肖十八码 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 2; adjacent: full ordered signature |
| 485 | wuzhong5ma | 内幕5不中 | number_exclusion | special number is absent from every candidate | controlled_future | supported | cross-site prefix: 2; adjacent: full ordered signature |
| 486 | daimingxiao | 代号生肖 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 487 | liuweichute | 六尾出特 | tail | special number tail is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 488 | toudanshuang | 头数单双 | head_parity | head_parity | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 489 | liuxiaoliuma | 六肖六码 | zodiac | special zodiac is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 490 | shaliangbanbo | 杀两半波 | half_wave_exclusion | special half-wave is absent from every candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 491 | gongshi_siw | 公式四尾 | tail | special number tail is in any candidate | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 492 | three_head_four_tail | 三头四尾 | head_tail | special number head OR tail is in its candidate group (mixed: any dimension) | controlled_future | supported | cross-site prefix: 1; adjacent: full ordered signature |
| 493 | selected_22_codes | 精选22码 | number | special number is in any candidate | controlled_future | supported | cross-site prefix: 3; adjacent: full ordered signature |
| 494 | steady_kill_7_codes | 稳杀7码 | number_exclusion | special number is absent from every candidate | controlled_future | supported | cross-site prefix: 2; adjacent: full ordered signature |
| 495 | expert_publications | 精准台湾高手资料 | blocked_pending_rule | blocked_pending_rule | history_only | blocked: missing_verified_rule | cross-site prefix: 1; adjacent: full ordered signature |
