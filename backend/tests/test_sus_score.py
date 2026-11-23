import importlib.util
import os

spec = importlib.util.spec_from_file_location("sus_score", os.path.join(os.path.dirname(__file__), "..", "scripts", "sus_score.py"))
sus_score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sus_score)


def test_sus_known_values():
    assert sus_score.sus([5, 1] * 5) == 100.0
    assert sus_score.sus([1, 5] * 5) == 0.0
    assert sus_score.sus([3] * 10) == 50.0
    assert sus_score.grade(85) == "A+" and sus_score.grade(68) == "C" and sus_score.grade(40) == "F"


def test_summary_from_form_rows():
    row = {f"SUS{i} statement": ("5 - Strongly agree" if i % 2 else "1 - Strongly disagree") for i in range(1, 11)}
    rows = [{**row, "Task 1 correct?": "Yes", "Comments": "nice"}, {**row, "Task 1 correct?": "No", "Comments": ""}]
    s = sus_score.summarise(rows)
    assert s["participants"] == 2 and s["sus_mean"] == 100.0 and s["task_success"]["Task 1 correct?"] == 0.5 and s["comments"] == ["nice"]
