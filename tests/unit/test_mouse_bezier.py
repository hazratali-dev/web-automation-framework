from src.infrastructure.browser.behaviors.mouse import bezier_path


def test_bezier_path_ends_at_target():
    path = bezier_path((0, 0), (100, 200), steps=10)
    assert len(path) == 10
    last_x, last_y = path[-1]
    assert abs(last_x - 100) < 1e-6
    assert abs(last_y - 200) < 1e-6


def test_bezier_path_is_not_a_straight_line():
    # A straight line would have every point exactly on the start->end line;
    # the randomized control point should push at least one point off it.
    path = bezier_path((0, 0), (100, 0), steps=10)
    assert any(abs(y) > 0.5 for _, y in path)
