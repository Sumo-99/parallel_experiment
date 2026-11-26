from vulnwatch.digest import relevant
from vulnwatch.provider import Advisory


def test_unscored_results_are_kept_in_rank_order():
    rs = [Advisory(title=str(i), url=str(i), content="", score=None) for i in range(3)]
    assert [a.url for a in relevant(rs, 0.45)] == ["0", "1", "2"]
