import unittest

from fastapi.testclient import TestClient

from app.database.connection import get_supabase
from app.main import app
from app.services.auth_service import get_current_user


OWNED_STUDENT_ID = "11111111-1111-1111-1111-111111111111"
OTHER_STUDENT_ID = "22222222-2222-2222-2222-222222222222"
FORMATION_ID = "33333333-3333-3333-3333-333333333333"


class _Result:
    def __init__(self, data):
        self.data = data


class _StudentsQuery:
    def __init__(self, owned_student_id: str):
        self.owned_student_id = owned_student_id
        self.filters = {}

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def single(self):
        return self

    def execute(self):
        if self.filters.get("user_id") == "user-1":
            return _Result({"id": self.owned_student_id})
        return _Result(None)


class _FakeSupabase:
    def __init__(self, owned_student_id: str):
        self.owned_student_id = owned_student_id

    def table(self, table_name: str):
        if table_name != "students":
            raise AssertionError(f"Unexpected table access in forbidden test: {table_name}")
        return _StudentsQuery(self.owned_student_id)


def _override_current_user():
    return {
        "id": "user-1",
        "email": "student@example.com",
        "role": "student",
    }


def _override_supabase():
    return _FakeSupabase(OWNED_STUDENT_ID)


def _build_client() -> TestClient:
    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_supabase] = _override_supabase
    return TestClient(app)


class StudentOwnershipSecurityTests(unittest.TestCase):
    def tearDown(self):
        app.dependency_overrides.clear()

    def test_student_cannot_access_other_student_profile_returns_403(self):
        with _build_client() as client:
            response = client.get(f"/students/{OTHER_STUDENT_ID}")
            self.assertEqual(response.status_code, 403)

    def test_student_cannot_access_other_student_formations_returns_403(self):
        with _build_client() as client:
            response = client.get(f"/students/{OTHER_STUDENT_ID}/formations")
            self.assertEqual(response.status_code, 403)

    def test_student_cannot_access_other_student_progress_returns_403(self):
        with _build_client() as client:
            response = client.get(f"/progress/student/{OTHER_STUDENT_ID}/formation/{FORMATION_ID}")
            self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()