from app.utils.style_guards import find_generic_empathy_phrase


def test_detects_generic_empathy_variants():
    assert find_generic_empathy_phrase("换谁做都很憋屈。")
    assert find_generic_empathy_phrase("任谁都很难接受。")
    assert find_generic_empathy_phrase("任何人碰到这样的情况都会觉得委屈。")
    assert find_generic_empathy_phrase("谁遇到这种情况都无法马上平静。")


def test_allows_specific_empathy():
    assert find_generic_empathy_phrase("被同学孤立了四个月，还一直得不到父母理解，这种夹在中间的压力很沉。") is None
