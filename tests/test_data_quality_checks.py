
from pathlib import Path
import ast


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "src" / "run_data_quality_checks.py"


def load_script():
    """Load the monitoring script without executing it."""
    return ast.parse(SCRIPT_PATH.read_text())


def test_data_quality_script_exists():
    """The monitoring script must exist."""
    assert SCRIPT_PATH.is_file()



def test_five_quality_checks_are_defined():
    """The script must define all five expected quality checks."""
    tree = load_script()

    check_names = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "QUALITY_CHECKS"
                ):
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for item in node.value.elts:
                            if isinstance(item, ast.Dict):
                                for key, value in zip(
                                    item.keys, item.values
                                ):
                                    if (
                                        isinstance(key, ast.Constant)
                                        and key.value == "check_name"
                                        and isinstance(value, ast.Constant)
                                    ):
                                        check_names.append(value.value)

    expected_checks = {
        "invalid_flight_schedule",
        "invalid_flight_route",
        "duplicate_crew_assignments",
        "assignments_without_current_history",
        "history_assignment_mismatch",
    }

    assert set(check_names) == expected_checks


def test_quality_checks_cover_expected_tables():
    """The checks must reference the relevant core tables."""
    script_text = SCRIPT_PATH.read_text()

    expected_tables = [
        "core.flights",
        "core.crew_assignments",
        "core.crew_assignment_history",
    ]

    for table in expected_tables:
        assert table in script_text
