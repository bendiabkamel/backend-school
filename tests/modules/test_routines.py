"""Tests for routine routes and conflict service."""

import unittest
from datetime import time

from fastapi.testclient import TestClient

from app.database.connection import get_supabase
from app.main import app
from app.services.auth_service import get_current_user
from app.services.routine_service import check_time_overlap, find_conflicts


class RoutineConflictServiceTests(unittest.TestCase):
    def test_overlap_returns_true_when_ranges_intersect(self):
        self.assertTrue(
            check_time_overlap(
                time(9, 0), time(10, 0),
                time(9, 30), time(10, 30),
            )
        )

    def test_overlap_returns_false_when_ranges_adjacent(self):
        self.assertFalse(
            check_time_overlap(
                time(9, 0), time(10, 0),
                time(10, 0), time(11, 0),
            )
        )

    def test_overlap_returns_false_when_no_intersection(self):
        self.assertFalse(
            check_time_overlap(
                time(9, 0), time(10, 0),
                time(11, 0), time(12, 0),
            )
        )

    def test_find_conflicts_different_weekday_no_conflict(self):
        existing = [
            {"id": "r1", "weekday": 2, "start_time": "09:00", "end_time": "10:00"},
        ]
        conflicts = find_conflicts(3, time(9, 0), time(10, 0), existing)
        self.assertEqual(conflicts, [])

    def test_find_conflicts_same_weekday_overlapping(self):
        existing = [
            {"id": "r1", "weekday": 1, "start_time": "09:00", "end_time": "10:00"},
        ]
        conflicts = find_conflicts(1, time(9, 30), time(10, 30), existing)
        self.assertEqual(len(conflicts), 1)

    def test_find_conflicts_excludes_self(self):
        existing = [
            {"id": "r1", "weekday": 1, "start_time": "09:00", "end_time": "10:00"},
        ]
        conflicts = find_conflicts(1, time(9, 0), time(10, 0), existing, exclude_id="r1")
        self.assertEqual(conflicts, [])


class _NoopTable:
    def select(self, *a, **kw):
        return self

    def insert(self, *a, **kw):
        return self

    def eq(self, *a, **kw):
        return self

    def order(self, *a, **kw):
        return self

    def execute(self):
        class _R:
            data = []

        return _R()


class _NoopSupabase:
    def table(self, name: str):
        return _NoopTable()


class RoutineRouteTests(unittest.TestCase):
    def tearDown(self):
        app.dependency_overrides.clear()

    def test_list_routines_unauthenticated_returns_401_or_403(self):
        with TestClient(app) as client:
            resp = client.get("/routines")
        self.assertIn(resp.status_code, (401, 403))

    def test_list_routines_authenticated_returns_200(self):
        app.dependency_overrides[get_supabase] = lambda: _NoopSupabase()
        app.dependency_overrides[get_current_user] = lambda: {
            "id": "u1",
            "role": "admin",
        }
        with TestClient(app) as client:
            resp = client.get("/routines")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_create_routine_invalid_time_returns_422(self):
        app.dependency_overrides[get_supabase] = lambda: _NoopSupabase()
        app.dependency_overrides[get_current_user] = lambda: {
            "id": "u1",
            "role": "admin",
        }
        import uuid

        with TestClient(app) as client:
            resp = client.post(
                "/routines",
                json={
                    "academic_session_id": str(uuid.uuid4()),
                    "semester_id": str(uuid.uuid4()),
                    "class_id": str(uuid.uuid4()),
                    "section_id": str(uuid.uuid4()),
                    "course_id": str(uuid.uuid4()),
                    "weekday": 1,
                    "start_time": "10:00:00",
                    "end_time": "09:00:00",  # end before start — invalid
                },
            )
        self.assertEqual(resp.status_code, 422)


if __name__ == "__main__":
    unittest.main()
