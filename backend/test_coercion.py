"""Quick smoke test for parameter coercion."""
from app.query_builder.param_coercion import coerce_parameters, _build_type_map
from datetime import date, datetime
import uuid

_build_type_map()

def test_date_coercion():
    params = {"hire_date_1": "2024-01-01"}
    field_map = {"hire_date_1": ("employees", "hire_date")}
    result = coerce_parameters("employees", params, field_map)
    assert isinstance(result["hire_date_1"], date), f"Expected date, got {type(result['hire_date_1'])}"
    print(f"PASS: str -> date: {result['hire_date_1']}")

def test_between_dates():
    params = {"hire_date_1_1": "2024-01-01", "hire_date_1_2": "2024-12-31"}
    field_map = {"hire_date_1_1": ("employees", "hire_date"), "hire_date_1_2": ("employees", "hire_date")}
    result = coerce_parameters("employees", params, field_map)
    assert isinstance(result["hire_date_1_1"], date)
    assert isinstance(result["hire_date_1_2"], date)
    print(f"PASS: BETWEEN dates: {result['hire_date_1_1']} to {result['hire_date_1_2']}")

def test_uuid_coercion():
    test_uuid = str(uuid.uuid4())
    params = {"id_1": test_uuid}
    field_map = {"id_1": ("employees", "id")}
    result = coerce_parameters("employees", params, field_map)
    assert isinstance(result["id_1"], uuid.UUID)
    print(f"PASS: str -> UUID: {result['id_1']}")

def test_numeric_coercion():
    params = {"budget_1": "50000.50"}
    field_map = {"budget_1": ("departments", "budget")}
    result = coerce_parameters("departments", params, field_map)
    assert isinstance(result["budget_1"], float)
    print(f"PASS: str -> float: {result['budget_1']}")

def test_integer_coercion():
    params = {"score_1": "4"}
    field_map = {"score_1": ("performance_reviews", "score")}
    result = coerce_parameters("performance_reviews", params, field_map)
    assert isinstance(result["score_1"], int)
    print(f"PASS: str -> int: {result['score_1']}")

def test_datetime_coercion():
    params = {"created_at_1": "2024-06-15T10:30:00"}
    field_map = {"created_at_1": ("employees", "created_at")}
    result = coerce_parameters("employees", params, field_map)
    assert isinstance(result["created_at_1"], datetime)
    print(f"PASS: str -> datetime: {result['created_at_1']}")

def test_invalid_date_error():
    try:
        params = {"hire_date_1": "not-a-date"}
        field_map = {"hire_date_1": ("employees", "hire_date")}
        coerce_parameters("employees", params, field_map)
        print("FAIL: Should have raised ValueError")
    except ValueError as e:
        print(f"PASS: Clean error: {e}")

def test_project_dates():
    params = {"start_date_1": "2024-03-01", "end_date_1": "2024-12-01"}
    field_map = {"start_date_1": ("projects", "start_date"), "end_date_1": ("projects", "end_date")}
    result = coerce_parameters("projects", params, field_map)
    assert isinstance(result["start_date_1"], date)
    assert isinstance(result["end_date_1"], date)
    print(f"PASS: Project dates: {result['start_date_1']} to {result['end_date_1']}")

def test_in_with_dates():
    params = {"date_1_0": "2024-01-01", "date_1_1": "2024-02-01", "date_1_2": "2024-03-01"}
    field_map = {
        "date_1_0": ("attendance", "date"),
        "date_1_1": ("attendance", "date"),
        "date_1_2": ("attendance", "date"),
    }
    result = coerce_parameters("attendance", params, field_map)
    for k in result:
        assert isinstance(result[k], date)
    print("PASS: IN dates coerced")

def test_enum_passthrough():
    params = {"status_1": "active"}
    field_map = {"status_1": ("employees", "status")}
    result = coerce_parameters("employees", params, field_map)
    assert isinstance(result["status_1"], str)
    print(f"PASS: Enum passthrough: {result['status_1']}")

if __name__ == "__main__":
    test_date_coercion()
    test_between_dates()
    test_uuid_coercion()
    test_numeric_coercion()
    test_integer_coercion()
    test_datetime_coercion()
    test_invalid_date_error()
    test_project_dates()
    test_in_with_dates()
    test_enum_passthrough()
    print("\nAll tests passed!")
