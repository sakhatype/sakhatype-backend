"""
Индекс сложности слова для SakhaType (синхронизируйте константы с sakhatype-frontend/src/lib/utils/wordDifficulty.js).

Формула (линейная смесь с отсечкой в [0, 1]):

    D(w) = clip( w_L · L̃ + w_ρ · ρ̃ + w_H · H + w_J · j , 0, 1 )

где
  • L̃ = min(L / L_max, 1)  — нормализованная эффективная длина;
    L считает «дь» и «нь» как одну позицию (как в разборе слогов).
  • ρ̃ = min(2·S/L, 1)  — насыщенная плотность якутских спецбукв {ҕ,ҥ,ө,ү,һ}
    (S — их количество в строке, L — эффективная длина; коэффициент 2 даёт вклад до 1 при ρ=0.5).
  • H ∈ [0,1]  — доля соседних пар символов, где ровно один из двух — спецбуква
    (модель «переключения» между обычной кириллицей и редкими клавишами).
  • j ∈ {0,1}  — есть ли пробел (многословные цели сложнее для набора).

Отбор:
  • normal (легкий): L ∈ [2, 7]; слова с L>5 (6–7 букв) — не более ~12% выборки (редко);
    ~⅓ слов с ≥1 спецбуквой; добор с теми же правилами длины/редкости длинных.
  • expert (сложный): пул с D ≥ D_expert_min; взвешенная выборка без повторов, вес ∝ D^γ
    (смещение к более трудным словам); при нехватке — ослабление порога.
    Слова с эффективной длиной L ≤ 4 — не более ~5% партии, если хватает более длинных.
"""

from __future__ import annotations

import random
from typing import List, Set, Tuple

MAX_EFFECTIVE_LENGTH = 15
YAKUT_SPECIAL = frozenset({"ҕ", "ҥ", "ө", "ү", "һ"})

W_L = 0.32
W_RHO = 0.38
W_H = 0.22
W_J = 0.12

# Пороги отбора expert (шкала D)
D_EXPERT_MIN = 0.30
D_EXPERT_MIN_RELAX = 0.22
EXPERT_WEIGHT_POWER = 2.4

# Сложный режим: короткие слова (L ≤ порога) — очень редко, если есть достаточно длинных
EXPERT_SHORT_EFFECTIVE_LEN_MAX = 4
EXPERT_SHORT_WORD_MAX_FRACTION = 0.05
EXPERT_SHORT_EXTRA_WEIGHT_FACTOR = 0.04  # при доборе с повтором — сильный штраф к весу коротких

# Лёгкий режим: L∈[2,7]; L>5 встречаются редко; ~⅓ слов со спецбуквой
NORMAL_EASY_LEN_MIN = 2
NORMAL_EASY_LEN_MAX = 7
NORMAL_EASY_SHORT_LEN_MAX = 5  # «короткие»; 6–7 букв — редкая доля
NORMAL_LONG_WORD_MAX_FRACTION = 0.12  # не более ~12% слов с L>5
NORMAL_SPECIAL_WORD_RATIO = 1.0 / 3.0


def effective_letter_count(word: str) -> int:
    lower = word.lower().strip()
    if not lower:
        return 0
    n = 0
    i = 0
    while i < len(lower):
        c0 = lower[i]
        c1 = lower[i + 1] if i + 1 < len(lower) else ""
        if c0 in ("д", "н") and c1 == "ь":
            n += 1
            i += 2
            continue
        n += 1
        i += 1
    return n


def count_yakut_special_chars(word: str) -> int:
    if not word:
        return 0
    return sum(1 for ch in word.lower() if ch in YAKUT_SPECIAL)


def _boundary_fraction(word: str) -> float:
    lower = word.lower().strip()
    if len(lower) < 2:
        return 0.0

    def is_spec(ch: str) -> bool:
        return ch in YAKUT_SPECIAL

    transitions = 0
    for i in range(len(lower) - 1):
        a, b = lower[i], lower[i + 1]
        if is_spec(a) != is_spec(b):
            transitions += 1
    return transitions / (len(lower) - 1)


def word_difficulty_score(word: str) -> float:
    """
    Возвращает D(w) ∈ [0, 1] по формуле выше.
    """
    w = word.strip() if isinstance(word, str) else ""
    length = effective_letter_count(w)
    if length == 0:
        return 0.0
    specials = count_yakut_special_chars(w)
    l_tilde = min(length / MAX_EFFECTIVE_LENGTH, 1.0)
    rho = specials / length
    rho_tilde = min(2.0 * rho, 1.0)
    h = _boundary_fraction(w)
    j = 1.0 if " " in w else 0.0
    raw = W_L * l_tilde + W_RHO * rho_tilde + W_H * h + W_J * j
    return max(0.0, min(1.0, raw))


def word_difficulty_label(word: str) -> str:
    d = word_difficulty_score(word)
    if d < 0.18:
        return "very_easy"
    if d < 0.32:
        return "easy"
    if d <= 0.48:
        return "medium"
    return "hard"


def _expert_weight(score: float) -> float:
    return max(0.001, float(score) ** EXPERT_WEIGHT_POWER)


def _expert_weights_for_extra_pick(words: List[str], base_weights: List[float]) -> List[float]:
    """Добор с повтором: сильно снижаем вес слов L ≤ EXPERT_SHORT_EFFECTIVE_LEN_MAX."""
    out: List[float] = []
    for w, bw in zip(words, base_weights):
        ln = effective_letter_count(w)
        if ln <= EXPERT_SHORT_EFFECTIVE_LEN_MAX:
            out.append(max(0.001, float(bw) * EXPERT_SHORT_EXTRA_WEIGHT_FACTOR))
        else:
            out.append(max(0.001, float(bw)))
    return out


def _pick_expert_weighted_sample(pool: List[Tuple[str, float]], count: int) -> List[str]:
    """
    Взвешенная выборка для expert: предпочитаем L > EXPERT_SHORT_EFFECTIVE_LEN_MAX;
    короткие (L ≤ порога) — не больше EXPERT_SHORT_WORD_MAX_FRACTION от count, когда возможно.
    """
    if not pool or count <= 0:
        return []
    words_only = [t[0] for t in pool]
    weights = [_expert_weight(s) for _, s in pool]

    max_short = max(0, round(count * EXPERT_SHORT_WORD_MAX_FRACTION))
    long_words = [w for w in words_only if effective_letter_count(w) > EXPERT_SHORT_EFFECTIVE_LEN_MAX]
    long_weights = [_expert_weight(s) for w, s in pool if effective_letter_count(w) > EXPERT_SHORT_EFFECTIVE_LEN_MAX]
    short_words = [w for w in words_only if effective_letter_count(w) <= EXPERT_SHORT_EFFECTIVE_LEN_MAX]
    short_weights = [_expert_weight(s) for w, s in pool if effective_letter_count(w) <= EXPERT_SHORT_EFFECTIVE_LEN_MAX]

    if not long_words:
        if len(words_only) >= count:
            return _weighted_sample_without_replacement(words_only, weights, count)
        first = _weighted_sample_without_replacement(words_only, weights, len(words_only))
        extra_w = _expert_weights_for_extra_pick(words_only, weights)
        first.extend(random.choices(words_only, weights=extra_w, k=count - len(first)))
        return first

    if len(long_words) >= count:
        return _weighted_sample_without_replacement(long_words, long_weights, count)

    long_first_cap = max(0, count - max_short)

    if len(long_words) >= long_first_cap:
        picked_long = _weighted_sample_without_replacement(long_words, long_weights, long_first_cap)
        need = count - len(picked_long)
        picked_short: List[str] = []
        if short_words and need > 0:
            take_short = min(need, len(short_words))
            picked_short = _weighted_sample_without_replacement(short_words, short_weights, take_short)
        out = picked_long + picked_short
        still = count - len(out)
        if still > 0:
            extra_w = _expert_weights_for_extra_pick(long_words, long_weights)
            out.extend(random.choices(long_words, weights=extra_w, k=still))
        return out

    picked_long = _weighted_sample_without_replacement(long_words, long_weights, len(long_words))
    need = count - len(picked_long)
    picked_short = (
        _weighted_sample_without_replacement(short_words, short_weights, min(need, len(short_words)))
        if short_words and need > 0
        else []
    )
    out = picked_long + picked_short
    still = count - len(out)
    if still > 0:
        extra_w = _expert_weights_for_extra_pick(words_only, weights)
        out.extend(random.choices(words_only, weights=extra_w, k=still))
    return out


def _weighted_sample_without_replacement(items: List[str], weights: List[float], k: int) -> List[str]:
    if not items or k <= 0:
        return []
    pool_i = list(range(len(items)))
    w = [max(0.001, float(x)) for x in weights]
    out: List[str] = []
    take = min(k, len(items))
    for _ in range(take):
        total = sum(w[i] for i in pool_i)
        r = random.random() * total
        acc = 0.0
        chosen_idx = pool_i[0]
        for idx in pool_i:
            acc += w[idx]
            if r <= acc:
                chosen_idx = idx
                break
        out.append(items[chosen_idx])
        pool_i.remove(chosen_idx)
    return out


def _shuffle_in_place(xs: List) -> None:
    for i in range(len(xs) - 1, 0, -1):
        j = random.randint(0, i)
        xs[i], xs[j] = xs[j], xs[i]


def _pick_from_spec_pairs(pairs: List[Tuple[str, bool]], count: int) -> List[str]:
    """До count слов из пар (слово, есть_спецбуква); ~NORMAL_SPECIAL_WORD_RATIO со спецбуквой."""
    if count <= 0 or not pairs:
        return []
    no_sp = [w for w, h in pairs if not h]
    wi_sp = [w for w, h in pairs if h]
    _shuffle_in_place(no_sp)
    _shuffle_in_place(wi_sp)
    spec_target = min(len(wi_sp), max(0, round(count * NORMAL_SPECIAL_WORD_RATIO)))
    plain_target = count - spec_target
    out: List[str] = []
    out.extend(wi_sp[:spec_target])
    out.extend(no_sp[:plain_target])
    used = set(out)
    rest = [w for w, _ in pairs if w not in used]
    _shuffle_in_place(rest)
    for w in rest:
        if len(out) >= count:
            break
        out.append(w)
    return out


def _build_short_long_pairs(raw: List[str]) -> Tuple[List[Tuple[str, bool]], List[Tuple[str, bool]]]:
    short_p: List[Tuple[str, bool]] = []
    long_p: List[Tuple[str, bool]] = []
    for w in raw:
        w = w.strip()
        if not w or " " in w:
            continue
        ln = effective_letter_count(w)
        if not (NORMAL_EASY_LEN_MIN <= ln <= NORMAL_EASY_LEN_MAX):
            continue
        has_spec = count_yakut_special_chars(w) > 0
        if ln <= NORMAL_EASY_SHORT_LEN_MAX:
            short_p.append((w, has_spec))
        else:
            long_p.append((w, has_spec))
    return short_p, long_p


def _pick_normal_easy_rare_long(raw: List[str], count: int) -> List[str]:
    """
    Лёгкий: в основном L≤5; слова с L>5 — не больше NORMAL_LONG_WORD_MAX_FRACTION от count.
    """
    short_pairs, long_pairs = _build_short_long_pairs(raw)
    long_target = min(count, max(0, round(count * NORMAL_LONG_WORD_MAX_FRACTION)))
    short_target = count - long_target

    short_words = [w for w, _ in short_pairs]
    long_words = [w for w, _ in long_pairs]

    part_s = _pick_from_spec_pairs(short_pairs, short_target)
    while len(part_s) < short_target:
        if short_words:
            part_s.append(random.choice(short_words))
        elif long_words:
            part_s.append(random.choice(long_words))
        else:
            break

    part_l = _pick_from_spec_pairs(long_pairs, long_target)
    while len(part_l) < long_target:
        if long_words:
            part_l.append(random.choice(long_words))
        elif short_words:
            part_l.append(random.choice(short_words))
        else:
            break

    out = part_s + part_l
    if len(out) > count:
        out = out[:count]
    return out


def _easy_vocab_split_short_long(
    raw: List[str],
) -> Tuple[List[str], List[str], List[str], List[str]]:
    """Уникальные L∈[2,7]: short без/со спецбуквой, long без/со спецбуквой."""
    s_no: List[str] = []
    s_yes: List[str] = []
    l_no: List[str] = []
    l_yes: List[str] = []
    seen: Set[str] = set()
    for w in raw:
        w = w.strip()
        if not w or " " in w or w in seen:
            continue
        ln = effective_letter_count(w)
        if not (NORMAL_EASY_LEN_MIN <= ln <= NORMAL_EASY_LEN_MAX):
            continue
        seen.add(w)
        spec = count_yakut_special_chars(w) > 0
        if ln <= NORMAL_EASY_SHORT_LEN_MAX:
            (s_yes if spec else s_no).append(w)
        else:
            (l_yes if spec else l_no).append(w)
    return s_no, s_yes, l_no, l_yes


def _pick_spec_from_vocab(no_sp: List[str], yes_sp: List[str]) -> str | None:
    if yes_sp and no_sp:
        return (
            random.choice(yes_sp)
            if random.random() < NORMAL_SPECIAL_WORD_RATIO
            else random.choice(no_sp)
        )
    if no_sp:
        return random.choice(no_sp)
    if yes_sp:
        return random.choice(yes_sp)
    return None


def _pad_normal_easy_to_count(picked: List[str], raw: List[str], count: int) -> None:
    """Добор L∈[2,7]; редко L>5; ~⅓ со спецбуквой."""
    need = count - len(picked)
    if need <= 0:
        return
    s_no, s_yes, l_no, l_yes = _easy_vocab_split_short_long(raw)
    if not (s_no or s_yes or l_no or l_yes):
        return

    long_cap = max(0, round(count * NORMAL_LONG_WORD_MAX_FRACTION))
    long_in_picked = sum(
        1
        for w in picked
        if NORMAL_EASY_SHORT_LEN_MAX < effective_letter_count(w) <= NORMAL_EASY_LEN_MAX
    )

    for _ in range(need):
        allow_long = long_in_picked < long_cap and (l_no or l_yes)
        want_long = allow_long and random.random() < NORMAL_LONG_WORD_MAX_FRACTION
        w: str | None
        if want_long:
            w = _pick_spec_from_vocab(l_no, l_yes) or _pick_spec_from_vocab(s_no, s_yes)
        else:
            w = _pick_spec_from_vocab(s_no, s_yes) or _pick_spec_from_vocab(l_no, l_yes)
        if not w:
            break
        picked.append(w)
        if NORMAL_EASY_SHORT_LEN_MAX < effective_letter_count(w) <= NORMAL_EASY_LEN_MAX:
            long_in_picked += 1


def pick_words_for_game_difficulty(words: List[str], game_difficulty: str, count: int) -> List[str]:
    """
    Умный подбор: normal — только L∈[2,7] и ~⅓ со спецбуквами; expert — bias к высокому D.
    """
    raw = [w.strip() for w in words if isinstance(w, str) and w.strip()]
    if not raw or count <= 0:
        return []

    if game_difficulty == "expert":
        scored: List[Tuple[str, float]] = [(w, word_difficulty_score(w)) for w in raw]
        pool = [x for x in scored if x[1] >= D_EXPERT_MIN]
        if len(pool) < count:
            pool = [x for x in scored if x[1] >= D_EXPERT_MIN_RELAX]
        if len(pool) < count:
            pool = list(scored)
        if not pool:
            return []
        return _pick_expert_weighted_sample(pool, count)

    # normal: L∈[2,7], редко L>5, ~⅓ со спецбуквами
    picked = _pick_normal_easy_rare_long(raw, count)
    if len(picked) < count:
        _pad_normal_easy_to_count(picked, raw, count)
    if len(picked) < count and picked:
        picked.extend(random.choices(picked, k=count - len(picked)))
    _shuffle_in_place(picked)
    return picked[:count]
