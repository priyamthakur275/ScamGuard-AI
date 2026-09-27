from ml_service.inference.confidence import ConfidenceCalculator, ConfidenceConfig


class TestConfidenceCalculator:
    def test_probability_at_boundary_yields_zero_confidence(self):
        calculator = ConfidenceCalculator()
        assert calculator.calculate(0.5) == 0.0

    def test_probability_at_one_yields_full_confidence(self):
        calculator = ConfidenceCalculator()
        assert calculator.calculate(1.0) == 1.0

    def test_probability_at_zero_yields_full_confidence(self):
        calculator = ConfidenceCalculator()
        assert calculator.calculate(0.0) == 1.0

    def test_confidence_is_symmetric_around_boundary(self):
        calculator = ConfidenceCalculator()
        below = calculator.calculate(0.3)
        above = calculator.calculate(0.7)
        assert below == above

    def test_result_is_always_within_unit_interval(self):
        calculator = ConfidenceCalculator()
        for probability in [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]:
            result = calculator.calculate(probability)
            assert 0.0 <= result <= 1.0

    def test_custom_decision_boundary_is_respected(self):
        calculator = ConfidenceCalculator(ConfidenceConfig(decision_boundary=0.7))
        assert calculator.calculate(0.7) == 0.0
