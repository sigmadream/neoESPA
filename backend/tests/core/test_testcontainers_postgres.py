import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.core.migrations import apply_migrations
from app.models.schemas import CollabCodeSnapshot, CollabParticipant, CollabSession, User

from .test_migrations import assert_all_migrations_applied, assert_latest_tables

@pytest.fixture(scope="module")
def postgres_engine():
    postgres_module = pytest.importorskip("testcontainers.postgres")
    container = None
    engine = None

    try:
        container = postgres_module.PostgresContainer("postgres:16-alpine")
        container.start()
        engine = create_engine(container.get_connection_url())
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        apply_migrations(engine)
    except Exception as exc:
        if engine is not None:
            engine.dispose()
        if container is not None:
            try:
                container.stop()
            except Exception:
                pass
        pytest.skip(f"Docker or Testcontainers is unavailable: {exc}")

    try:
        yield engine
    finally:
        engine.dispose()
        container.stop()



def test_postgres_migrations_create_latest_schema(postgres_engine):
    assert_latest_tables(postgres_engine)
    assert_all_migrations_applied(postgres_engine)

    inspector = inspect(postgres_engine)
    unique_constraints = inspector.get_unique_constraints("collab_participants")
    indexes = inspector.get_indexes("collab_code_snapshots")

    assert any(
        set(constraint["column_names"]) == {"session_id", "user_id"}
        for constraint in unique_constraints
    )
    assert any(index["column_names"] == ["session_id", "created_at"] for index in indexes)



def test_postgres_collab_snapshot_round_trip_and_uniqueness(postgres_engine):
    long_code = "print('postgres smoke')\n" * 2048

    with Session(postgres_engine) as session:
        mentor = User(
            id="pg-mentor",
            sid=10062001,
            ps="hashed-password",
            name="pg-mentor",
            phone="010-0000-0001",
            email="pg-mentor@example.com",
            user_group="admin",
        )
        member = User(
            id="pg-member",
            sid=20262001,
            ps="hashed-password",
            name="pg-member",
            phone="010-0000-0002",
            email="pg-member@example.com",
            user_group="student",
        )
        session.add(mentor)
        session.add(member)
        session.commit()

        collab_session = CollabSession(
            title="Postgres Smoke Session",
            mentor_id=mentor.id,
            current_code=long_code,
        )
        session.add(collab_session)
        session.commit()
        session.refresh(collab_session)

        session.add(
            CollabParticipant(
                session_id=collab_session.id,
                user_id=member.id,
                role="member",
                can_edit=True,
            )
        )
        session.commit()

        session.add(
            CollabParticipant(
                session_id=collab_session.id,
                user_id=member.id,
                role="member",
                can_edit=True,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        snapshot = CollabCodeSnapshot(
            session_id=collab_session.id,
            user_id=member.id,
            code_text=long_code,
        )
        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)

        stored_snapshot = session.get(CollabCodeSnapshot, snapshot.id)

    assert stored_snapshot is not None
    assert stored_snapshot.code_text == long_code
    assert stored_snapshot.created_at is not None
