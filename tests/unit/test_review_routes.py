"""Tests for the review routes."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.middleware.auth import get_current_user
from core.database import get_db


class _Result:
    def __init__(self, obj):
        self._obj = obj

    def scalars(self):
        return self

    def first(self):
        return self._obj


def _session(profile):
    """Build a stand-in db session. Profile queries return `profile`."""
    created = {}
    db = AsyncMock()
    db.add = Mock(side_effect=lambda obj: created.__setitem__("review", obj))
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    async def refresh(obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        now = datetime.now(UTC)
        obj.created_at = getattr(obj, "created_at", None) or now
        obj.updated_at = getattr(obj, "updated_at", None) or now

    db.refresh = AsyncMock(side_effect=refresh)

    async def execute(stmt):
        text = str(stmt).lower()
        if "profiles" in text:
            return _Result(profile)
        return _Result(created.get("review"))

    db.execute = AsyncMock(side_effect=execute)
    return db, created


def _post(profile, profile_id):
    db, created = _session(profile)
    user = SimpleNamespace(id=uuid4())

    async def override_db():
        yield db

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).post("/reviews", json={"profile_id": str(profile_id)})
    finally:
        app.dependency_overrides.clear()
    return response, created


@pytest.mark.unit
def test_post_reviews_rejects_profile_with_no_ingested_documents():
    """POST /reviews returns 422 when the profile has nothing to ingest."""
    profile_id = uuid4()
    profile = SimpleNamespace(
        id=profile_id,
        github_username=None,
        portfolio_url=None,
        resume_text=None,
        resume_filename=None,
    )

    response, created = _post(profile, profile_id)

    assert response.status_code == 422
    assert response.json()["detail"] == "Profile has no ingested documents"
    assert "review" not in created


@pytest.mark.unit
def test_post_reviews_rejects_blank_source_fields():
    """Blank strings are not ingested documents."""
    profile_id = uuid4()
    profile = SimpleNamespace(
        id=profile_id,
        github_username="  ",
        portfolio_url="",
        resume_text=None,
        resume_filename=None,
    )

    response, created = _post(profile, profile_id)

    assert response.status_code == 422
    assert "review" not in created


@pytest.mark.unit
def test_post_reviews_returns_404_when_profile_is_missing():
    """The same lookup returns 404 when the profile row does not exist."""
    response, created = _post(None, uuid4())

    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found"
    assert "review" not in created
