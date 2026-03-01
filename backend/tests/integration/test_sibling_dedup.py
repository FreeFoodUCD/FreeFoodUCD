"""
Integration tests for A11 sibling-segment dedup logic.

Two tests at different levels:

  test_sibling_dedup_sql_logic
      Pure SQL: verifies that ~Event.id.in_(created_this_run_uuids) correctly
      excludes a just-flushed sibling event from the same-day duplicate query.
      Uses a single real PostgreSQL session; rolls back at the end — nothing
      is committed to the DB.

  test_sibling_segments_both_create_events
      End-to-end: a 2-segment food-event post processed through
      _process_scraped_content_async must produce 2 Event rows, not 1.
      Without the created_this_run_uuids fix, the second segment would be
      blocked by the same-day dedup because the first segment's event already
      exists in the same society × same day.

Run with:
    cd backend && pytest tests/integration/test_sibling_dedup.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.models import Society, Post, Event
from app.workers.scraping_tasks import _process_scraped_content_async


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_engine():
    return create_async_engine(settings.DATABASE_URL, poolclass=NullPool)


# ── Test 1: SQL dedup logic (no NLP, pure SQL, rollback) ─────────────────────

@pytest.mark.asyncio
async def test_sibling_dedup_sql_logic():
    """
    Directly test the same-day dedup SQL clause used in _process_scraped_content_async.

    The function tracks events created earlier in the same run via
    `created_this_run_uuids` and excludes them with:
        ~Event.id.in_(created_this_run_uuids)

    Without that exclusion, segment 2 would see segment 1's just-created event
    in the same-day query and treat it as a duplicate — incorrectly blocking
    the second food event from being stored.
    """
    engine = _make_engine()
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            # -- Setup: create test society + one sibling event (not committed) --
            society = Society(
                name="SQL Dedup Test Society",
                instagram_handle=f"_test_sql_{uuid.uuid4().hex[:8]}",
            )
            session.add(society)
            await session.flush()

            tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
            sibling_start = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)

            sibling = Event(
                society_id=society.id,
                title="Pancake Morning (sibling segment 1)",
                start_time=sibling_start,
                source_type='post',
                source_id=uuid.uuid4(),
                is_active=True,
                confidence_score=0.9,
            )
            session.add(sibling)
            await session.flush()   # visible within this session; not committed

            day_start = sibling_start.replace(hour=0, minute=0, second=0, microsecond=0)

            # -- Query WITHOUT sibling exclusion --
            # Simulates what happens when created_this_run_uuids is empty (or ignored).
            # The sibling event IS found → segment 2 would be incorrectly blocked.
            result_without = (
                await session.execute(
                    select(Event).where(
                        Event.society_id == society.id,
                        Event.start_time >= day_start,
                        Event.start_time < day_start + timedelta(days=1),
                        Event.is_active == True,
                    )
                )
            ).scalars().all()

            assert len(result_without) == 1, (
                "Without sibling exclusion the same-day query must find the sibling "
                "(demonstrating why the fix is needed)"
            )

            # -- Query WITH sibling exclusion --
            # Simulates the actual fix: created_this_run_uuids = [sibling.id]
            # The sibling event is excluded → result is empty → segment 2 is NOT a duplicate.
            result_with = (
                await session.execute(
                    select(Event).where(
                        Event.society_id == society.id,
                        Event.start_time >= day_start,
                        Event.start_time < day_start + timedelta(days=1),
                        Event.is_active == True,
                        ~Event.id.in_([sibling.id]),    # created_this_run_uuids exclusion
                    )
                )
            ).scalars().all()

            assert len(result_with) == 0, (
                "With sibling exclusion the same-day query must return empty — "
                "segment 2 should not be treated as a duplicate of segment 1"
            )

            await session.rollback()    # nothing committed; DB is unchanged
    finally:
        await engine.dispose()


# ── Test 2: End-to-end pipeline (commits setup, cleans up) ───────────────────

# A 2-segment post where both segments are clear food events.
# No explicit date → extract_event uses datetime.now() as date → both events
# land on today.  Times are 3 hours apart so the ±1 hour global dedup doesn't
# fire; only the same-day society dedup is relevant.
_E2E_CAPTION = (
    "PANCAKE SOCIAL\n"
    "Come join us for free pancakes at 11am! Newman Building 11am-12pm.\n\n"
    "COFFEE MORNING\n"
    "Free coffee and biscuits at 2pm. Newman Building room G15 2pm-3pm."
)


@pytest_asyncio.fixture
async def multi_event_post():
    """
    Create a test Society + Post in the real DB, yield their IDs, then
    delete all generated rows (Events, Post, Society) on teardown.
    """
    engine = _make_engine()
    society_id = None
    post_id = None

    try:
        # -- Setup --
        async with AsyncSession(engine, expire_on_commit=False) as session:
            society = Society(
                name="Sibling Dedup E2E Test Society",
                instagram_handle=f"_test_e2e_{uuid.uuid4().hex[:8]}",
            )
            session.add(society)
            await session.flush()
            society_id = society.id

            post = Post(
                society_id=society_id,
                instagram_post_id=f"_test_{uuid.uuid4().hex}",
                caption=_E2E_CAPTION,
                source_url="https://instagram.com/p/_test",
                media_urls=None,            # skip OCR
                detected_at=datetime.now(timezone.utc),
                processed=False,
            )
            session.add(post)
            await session.commit()
            post_id = post.id

        yield {"society_id": society_id, "post_id": post_id}

    finally:
        # -- Teardown: remove all rows generated by this test --
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await session.execute(delete(Event).where(Event.society_id == society_id))
            await session.execute(delete(Post).where(Post.society_id == society_id))
            await session.execute(delete(Society).where(Society.id == society_id))
            await session.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_sibling_segments_both_create_events(multi_event_post):
    """
    End-to-end: processing a 2-segment food-event post must create 2 Event rows.

    The same-day society dedup checks whether any event for the same society
    already exists on the same day.  Without created_this_run_uuids, segment 2
    would see segment 1's freshly created event and be skipped as a duplicate.
    The fix excludes sibling events from that check, allowing both to be stored.
    """
    result = await _process_scraped_content_async(
        "post", str(multi_event_post["post_id"])
    )

    assert result["event_created"] is True, (
        "At least one event should be created from the multi-segment caption"
    )
    assert len(result["event_ids"]) == 2, (
        f"Expected 2 events (one per food segment), got {len(result['event_ids'])}.\n"
        f"If only 1, the sibling dedup fix (created_this_run_uuids) may be broken."
    )
