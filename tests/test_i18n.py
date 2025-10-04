from main import I18N, t

def test_all_languages_have_keys():
    keys_en = set(I18N["en"].keys())
    keys_pt = set(I18N["pt"].keys())
    missing_pt = keys_en - keys_pt
    missing_en = keys_pt - keys_en
    assert not missing_pt, f"Missing in PT: {missing_pt}"
    assert not missing_en, f"Missing in EN: {missing_en}"

def test_translation_returns_fallback():
    assert t("en", "nonexistent_key") == "nonexistent_key"
