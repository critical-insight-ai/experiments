"""Tests for cognos_measure.compression module."""

from cognos_measure.compression import (
    code_activation_ratio,
    cognitive_load_estimate,
    compression_stack,
    specification_sparsity,
)


def test_specification_sparsity():
    result = specification_sparsity(1_178_432, 3_611)
    assert result["sparsity_ratio"] == 326.3  # approx 326:1
    assert result["label"] == "326:1"


def test_code_activation_ratio():
    result = code_activation_ratio(1_178_432, 275_000)
    assert result["activation_ratio"] == 4.3
    assert result["activation_pct"] == 23.3


def test_compression_stack():
    layers = [
        {"name": "signal", "input_size": 32, "output_size": 3},
        {"name": "architecture", "input_size": 671, "output_size": 37},
        {"name": "semantic", "input_size": 1_178_432, "output_size": 3_611},
    ]
    result = compression_stack(layers)
    assert result["total_layers"] == 3
    assert result["cumulative_ratio"] > 1


def test_cognitive_load_fits():
    # 20 CRDs * 8 fields = 160 < 343
    result = cognitive_load_estimate(20)
    assert result["fits_in_memory"] is True
    assert result["utilization_pct"] < 100


def test_cognitive_load_exceeds():
    # 100 CRDs * 8 fields = 800 > 343
    result = cognitive_load_estimate(100)
    assert result["fits_in_memory"] is False
