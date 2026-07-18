"""Document expected ScreenLine to Home Assistant conversions."""


def coverage_to_ha(value):
    return max(0, min(100, 100 - round(float(value))))


def inclination_to_ha(value):
    return max(0, min(100, round(100 * (1 - min(abs(float(value)), 75) / 75))))


def test_coverage_78_is_22_percent_open():
    assert coverage_to_ha(78) == 22


def test_only_full_coverage_is_closed():
    assert coverage_to_ha(100) == 0
    assert coverage_to_ha(99) == 1


def test_tilt_horizontal_is_open():
    assert inclination_to_ha(0) == 100


def test_both_tilt_extremes_are_closed():
    assert inclination_to_ha(75) == 0
    assert inclination_to_ha(-75) == 0
