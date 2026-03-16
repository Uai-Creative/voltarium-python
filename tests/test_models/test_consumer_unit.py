"""Tests for consumer unit code generation."""

import pytest

from voltarium.sandbox.consumer_unit import generate_consumer_unit_code


class TestGenerateConsumerUnitCode:
    """Tests for the generate_consumer_unit_code function."""

    def test_returns_15_digit_string(self):
        code = generate_consumer_unit_code("1234567890123")
        assert len(code) == 15
        assert code.isdigit()

    def test_pads_short_base(self):
        code = generate_consumer_unit_code("1")
        assert len(code) == 15
        assert code[:12] == "000000000000"  # 12 leading zeros before "1"

    def test_truncates_long_base(self):
        code = generate_consumer_unit_code("12345678901234567890")
        assert len(code) == 15
        assert code[:13] == "1234567890123"

    def test_known_code_check_digits(self):
        # Verified against CCEE sandbox API
        assert generate_consumer_unit_code("0000010000004") == "000001000000471"

    @pytest.mark.parametrize(
        "base",
        [
            "0000010000004",
            "0000100000777",
            "0001000001234",
            "1000001000042",
            "0000000000001",
        ],
    )
    def test_check_digits_are_valid(self, base: str):
        """Verify check digits pass modulo-11 validation."""
        code = generate_consumer_unit_code(base)

        # Re-validate N2
        digits = [int(d) for d in code[:13]]
        weights_n2 = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 10, 9, 8]
        remainder = sum(d * w for d, w in zip(digits, weights_n2, strict=True)) % 11
        expected_n2 = 0 if remainder < 2 else 11 - remainder
        assert int(code[13]) == expected_n2

        # Re-validate N1
        digits_14 = [int(d) for d in code[:14]]
        weights_n1 = [11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 10, 9, 8]
        remainder = sum(d * w for d, w in zip(digits_14, weights_n1, strict=True)) % 11
        expected_n1 = 0 if remainder < 2 else 11 - remainder
        assert int(code[14]) == expected_n1

    def test_different_bases_produce_different_codes(self):
        code1 = generate_consumer_unit_code("0000010000001")
        code2 = generate_consumer_unit_code("0000010000002")
        assert code1 != code2
