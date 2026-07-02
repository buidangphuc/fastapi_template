from app.modules.business.listing.generation.utils import (
    cvt_shorten_number,
    number_standardize,
    random_use,
    random_use_one_in_list,
)


def test_number_standardize():
    assert number_standardize(0.2) == 0.2
    assert number_standardize(1.0) == 1
    assert number_standardize(1.2) == 1.2
    assert number_standardize(21.0) == 21
    assert number_standardize(None) is None


def test_cvt_shorten_number():
    assert cvt_shorten_number(2_500_000_000) == "2,5 tỷ"
    assert cvt_shorten_number(1_000_000_000) == "1 tỷ"
    assert cvt_shorten_number(100_000_000) == "100 triệu"
    assert cvt_shorten_number(8_000_000) == "8 triệu"


def test_random_use_extremes():
    assert random_use("yes", "no", weights=1) == "yes"
    assert random_use("yes", "no", weights=0) == "no"
    assert random_use("yes", "no", weights=1, condition=False) == "no"


def test_random_use_one_in_list_weighted():
    assert random_use_one_in_list(["a", "b", "c"], weights=[1.0, 0.0, 0.0]) == "a"
    assert random_use_one_in_list(["only"]) == "only"
