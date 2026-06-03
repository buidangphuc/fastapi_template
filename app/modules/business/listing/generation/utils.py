"""Number / string / randomization helpers for the generator.

Ported verbatim from bds-genai-dgl ``common/utils/{number,string,random}.py``
(only the functions the generator uses). Behavior-frozen.
"""

from __future__ import annotations

import numpy as np


def number_standardize(x: float | int | None) -> float | int | None:
    """0.2 -> 0.2, 1.0 -> 1, 1.2 -> 1.2, 21.0 -> 21, None -> None."""
    if x is None:
        return None
    if int(x) == x:
        return int(x)
    return x


def cvt_shorten_number(number: float) -> str:
    """Convert a number to a short VN form (e.g. 2_500_000_000 -> '2,5 tỷ')."""
    units = [(1_000_000_000, "tỷ"), (1_000_000, "triệu"), (1_000, "nghìn")]

    for unit_value, unit_name in units:
        if number >= unit_value:
            short_number = number / unit_value
            if short_number.is_integer():
                return f"{int(short_number)} {unit_name}"
            short_number = (
                int(short_number)
                if round(short_number, 3) % 1 < 0.009
                else round(short_number, 3)
            )
            return (
                f"{short_number:.3f}".replace(".", ",").rstrip("0").rstrip(",")
                + f" {unit_name}"
            )

    number = int(number) if round(number, 3) % 1 < 0.009 else round(number, 3)
    return f"{number:.3f}".replace(".", ",").rstrip("0").rstrip(",")


def random_use(
    prompt: str,
    other_prompt: str = "",
    weights: float = 0.5,
    condition: bool | None = None,
) -> str:
    """Randomly return ``prompt`` (prob ``weights``) else ``other_prompt``."""
    if condition is None:
        condition = True
    if condition and np.random.choice([0, 1], p=[1 - weights, weights]):
        return prompt
    return other_prompt


def random_use_one_in_list(prompts: list, weights: list | None = None) -> str:
    """Randomly pick one prompt from ``prompts`` by ``weights`` (uniform if None)."""
    if weights is None:
        weights = [1 / len(prompts)] * len(prompts)
    return np.random.choice(prompts, p=weights)
