from scripts.render_thesis_figures import FIGURES, GENERATOR_ORDER, _selected


def test_manifest_covers_all_manuscript_figures() -> None:
    assert [figure.number for figure in FIGURES] == [
        "3.1",
        "6.1",
        "6.2",
        "6.3",
        "7.1",
        "7.2",
        "8.1",
        "8.2",
        "8.3",
        "8.4",
        "9.1",
        "9.2",
        "9.3",
    ]
    assert len({figure.stem for figure in FIGURES}) == len(FIGURES)
    assert {figure.generator for figure in FIGURES} == set(GENERATOR_ORDER)


def test_selection_preserves_manuscript_order() -> None:
    assert [figure.number for figure in _selected(["9.3", "6.1"])] == [
        "6.1",
        "9.3",
    ]
