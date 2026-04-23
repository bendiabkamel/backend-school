import unittest

from fastapi.testclient import TestClient

from app.database.connection import get_supabase
from app.main import app
from app.services.auth_service import get_current_user


class _NoopTable:
    def __init__(self, name: str):
        self.name = name

    def select(self, *args, **kwargs):
        return self

    def insert(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def upsert(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        class _Result:
            data = []

        return _Result()


class _NoopSupabase:
    def table(self, name: str):
        return _NoopTable(name)


class Phase3RouteTests(unittest.TestCase):
    def tearDown(self):
        app.dependency_overrides.clear()

    def test_school_session_create_invalid_dates_returns_422(self):
        app.dependency_overrides[get_supabase] = lambda: _NoopSupabase()
        app.dependency_overrides[get_current_user] = lambda: {"id": "admin-1", "role": "admin"}
        with TestClient(app) as client:
            response = client.post(
                "/school-sessions",
                json={
                    "session_name": "2026",
                    "starts_on": "2026-06-01",
                    "ends_on": "2026-01-01",
                    "status": "draft",
                },
            )
        self.assertEqual(response.status_code, 422)

    def test_attendance_bulk_invalid_payload_returns_422(self):
        app.dependency_overrides[get_supabase] = lambda: _NoopSupabase()
        app.dependency_overrides[get_current_user] = lambda: {"id": "teacher-1", "role": "formateur"}
        with TestClient(app) as client:
            response = client.post("/attendance-v2", json={"records": []})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
