"""Tests for teacher routes."""

import unittest
from fastapi.testclient import TestClient

from app.database.connection import get_supabase
from app.main import app
from app.services.auth_service import get_current_user


class _NoopTable:
    def __init__(self, name: str = ""):
        self._data: list = []

    def select(self, *a, **kw):
        return self

    def insert(self, *a, **kw):
        self._pending = a[0] if a else {}
        return self

    def update(self, *a, **kw):
        return self

    def upsert(self, *a, **kw):
        self._pending = a[0] if a else {}
        return self

    def delete(self, *a, **kw):
        return self

    def eq(self, *a, **kw):
        return self

    def or_(self, *a, **kw):
        return self

    def order(self, *a, **kw):
        return self

    def single(self, *a, **kw):
        return self

    def execute(self):
        class _R:
            data = []

        return _R()


class _NoopSupabase:
    def table(self, name: str):
        return _NoopTable(name)


def _admin():
    return {"id": "admin-1", "role": "admin"}


def _formateur():
    return {"id": "teacher-1", "role": "formateur"}


class TeacherRouteTests(unittest.TestCase):
    def tearDown(self):
        app.dependency_overrides.clear()

    def test_list_teachers_requires_auth(self):
        """GET /teachers without auth returns 403 or 401."""
        with TestClient(app) as client:
            resp = client.get("/teachers")
        self.assertIn(resp.status_code, (401, 403))

    def test_list_teachers_formateur_allowed(self):
        app.dependency_overrides[get_supabase] = lambda: _NoopSupabase()
        app.dependency_overrides[get_current_user] = lambda: _formateur()
        with TestClient(app) as client:
            resp = client.get("/teachers")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_create_teacher_missing_email_returns_422(self):
        app.dependency_overrides[get_supabase] = lambda: _NoopSupabase()
        app.dependency_overrides[get_current_user] = lambda: _admin()
        with TestClient(app) as client:
            resp = client.post("/teachers", json={"full_name": "John Doe"})
        self.assertEqual(resp.status_code, 422)

    def test_update_teacher_non_admin_own_profile_allowed(self):
        """A formateur can update their own profile."""
        app.dependency_overrides[get_supabase] = lambda: _NoopSupabase()
        app.dependency_overrides[get_current_user] = lambda: {
            "id": "teacher-1",
            "role": "formateur",
        }
        with TestClient(app) as client:
            resp = client.put(
                "/teachers/teacher-1",
                json={"full_name": "Updated Name"},
            )
        # Noop supabase returns empty data so 404, but not 403
        self.assertNotEqual(resp.status_code, 403)

    def test_update_teacher_other_profile_forbidden(self):
        """A formateur cannot update another teacher's profile."""
        app.dependency_overrides[get_supabase] = lambda: _NoopSupabase()
        app.dependency_overrides[get_current_user] = lambda: {
            "id": "teacher-1",
            "role": "formateur",
        }
        import uuid

        other_id = str(uuid.uuid4())
        with TestClient(app) as client:
            resp = client.put(f"/teachers/{other_id}", json={"full_name": "X"})
        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
