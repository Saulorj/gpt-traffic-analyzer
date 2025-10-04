import math
from main import compute_metrics, stability_score

def test_stability_score_scale():
    score, verdict = stability_score(0, 0)
    assert 90 <= score <= 100
    assert verdict in {"excellent", "good", "fair", "poor", "very_poor"}

def test_score_penalizes_loss_and_jitter():
    base_score, _ = stability_score(0, 0)
    low_score, _ = stability_score(50, 10)
    assert low_score < base_score

def test_compute_metrics_basic():
    rtts = [10, 20, 30, 40, 50]
    result = compute_metrics(rtts, sent=5, received=5)
    assert math.isclose(result["avg"], 30, rel_tol=0.1)
    assert result["loss_pct"] == 0
