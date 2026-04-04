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
  • normal (легкий): только одно слово (без пробела), длина L ∈ [2, 7] (эффективная);
    из выборки примерно ⌊count/3 + 0.5⌋ слов с ≥1 спецбуквой, остальные без спецбукв (~1 «особое» на 3 слова);
    при нехватке — добор только повторениями из того же пула L∈[2,7] (длинные слова не подмешиваются).
  • expert (сложный): пул с D ≥ D_expert_min; взвешенная выборка без повторов, вес ∝ D^γ
    (смещение к более трудным словам); при нехватке — ослабление порога.
"""

from __future__ import annotations

import random
from typing import List, Optional, Set, Tuple

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

# Лёгкий режим: короткие слова и редкие спецбуквы (~⅓ слов со спецсимволом)
NORMAL_EASY_LEN_MIN = 2
NORMAL_EASY_LEN_MAX = 7
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


def _pick_normal_easy_bounded(
    raw: List[str],
    count: int,
    len_max: int,
    exclude: Optional[Set[str]] = None,
) -> List[str]:
    """
    Одно слово, L ∈ [2, len_max], без пробела; ~ratio слов с ≥1 спецбуквой, остальные без.
    """
    banned = exclude if exclude is not None else set()
    eligible: List[Tuple[str, bool]] = []
    for w in raw:
        w = w.strip()
        if not w or " " in w or w in banned:
            continue
        ln = effective_letter_count(w)
        if not (NORMAL_EASY_LEN_MIN <= ln <= len_max):
            continue
        has_spec = count_yakut_special_chars(w) > 0
        eligible.append((w, has_spec))

    if not eligible:
        return []

    no_sp = [w for w, h in eligible if not h]
    wi_sp = [w for w, h in eligible if h]
    _shuffle_in_place(no_sp)
    _shuffle_in_place(wi_sp)

    spec_target = min(len(wi_sp), max(0, round(count * NORMAL_SPECIAL_WORD_RATIO)))
    plain_target = count - spec_target

    out: List[str] = []
    out.extend(wi_sp[:spec_target])
    out.extend(no_sp[:plain_target])

    used = set(out)
    rest = [w for w, _ in eligible if w not in used]
    _shuffle_in_place(rest)
    for w in rest:
        if len(out) >= count:
            break
        out.append(w)

    return out


def _easy_vocab_split(raw: List[str]) -> Tuple[List[str], List[str]]:
    """Уникальные слова L∈[2,7], без пробела: без спецбукв / со спецбуквой."""
    no_sp: List[str] = []
    wi_sp: List[str] = []
    seen: Set[str] = set()
    for w in raw:
        w = w.strip()
        if not w or " " in w or w in seen:
            continue
        ln = effective_letter_count(w)
        if not (NORMAL_EASY_LEN_MIN <= ln <= NORMAL_EASY_LEN_MAX):
            continue
        seen.add(w)
        if count_yakut_special_chars(w) > 0:
            wi_sp.append(w)
        else:
            no_sp.append(w)
    return no_sp, wi_sp


def _pad_normal_easy_to_count(picked: List[str], raw: List[str], count: int) -> None:
    """Добирает до count только словами L∈[2,7]; ~⅓ слотов — со спецбуквой (если есть)."""
    need = count - len(picked)
    if need <= 0:
        return
    no_sp, wi_sp = _easy_vocab_split(raw)
    if not no_sp and not wi_sp:
        return
    for _ in range(need):
        if wi_sp and no_sp:
            if random.random() < NORMAL_SPECIAL_WORD_RATIO:
                picked.append(random.choice(wi_sp))
            else:
                picked.append(random.choice(no_sp))
        elif no_sp:
            picked.append(random.choice(no_sp))
        else:
            picked.append(random.choice(wi_sp))


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
        weights = [max(0.001, s**EXPERT_WEIGHT_POWER) for _, s in pool]
        words_only = [t[0] for t in pool]
        if not words_only:
            return []
        if len(words_only) >= count:
            return _weighted_sample_without_replacement(words_only, weights, count)
        first = _weighted_sample_without_replacement(words_only, weights, len(words_only))
        extra = random.choices(words_only, weights=weights, k=count - len(first))
        return first + extra

    # normal: только L∈[2,7], ~⅓ со спецбуквами; без подмешивания длинных слов
    picked = _pick_normal_easy_bounded(raw, count, NORMAL_EASY_LEN_MAX)
    if len(picked) < count:
        _pad_normal_easy_to_count(picked, raw, count)
    if len(picked) < count and picked:
        picked.extend(random.choices(picked, k=count - len(picked)))
    _shuffle_in_place(picked)
    return picked[:count]
