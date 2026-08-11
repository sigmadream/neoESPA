import hashlib

from sqlmodel import select

from app.models.schemas import ProblemAsset, ProblemTestCase
from app.services.artifact_store import LocalArtifactStore


def _draft_problem(client, create_user, login_user, auth_headers):
    create_user("asset-admin", 20259101, "password", role="admin")
    headers = auth_headers(login_user("asset-admin"))
    problem = client.post(
        "/api/admin/problems",
        json={
            "code": "artifact-problem",
            "title": "Artifact Problem",
            "statement": "Statement",
        },
        headers=headers,
    ).json()
    revision = client.get(
        f"/api/admin/problems/{problem['id']}/revisions", headers=headers
    ).json()[0]
    return problem, revision, headers


def test_artifact_store_deduplicates_and_verifies(tmp_path):
    store = LocalArtifactStore(tmp_path / "bundle")
    first = store.put_bytes(b"same-content")
    second = store.put_bytes(b"same-content")

    assert first.sha256 == hashlib.sha256(b"same-content").hexdigest()
    assert first.relative_path == second.relative_path
    assert store.resolve(first.relative_path, first.sha256).read_bytes() == b"same-content"
    assert len(list((tmp_path / "bundle" / "objects").rglob(first.sha256))) == 1


def test_admin_can_manage_testcase_files(
    client,
    session,
    create_user,
    login_user,
    auth_headers,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("COURSE_BUNDLE_ROOT", str(tmp_path / "course"))
    problem, revision, headers = _draft_problem(
        client, create_user, login_user, auth_headers
    )
    base = f"/api/admin/problems/{problem['id']}/revisions/{revision['id']}"

    created = client.post(
        f"{base}/testcases",
        data={"case_name": "case-1", "position": 1, "score": 100, "is_sample": "false"},
        files={
            "input_file": ("1.in", b"1 2\n", "text/plain"),
            "output_file": ("1.out", b"3\n", "text/plain"),
        },
        headers=headers,
    )

    assert created.status_code == 201, created.text
    testcase = created.json()
    assets = client.get(f"{base}/assets", headers=headers)
    assert assets.status_code == 200
    assert len(assets.json()) == 2
    assert all(asset["is_hidden"] for asset in assets.json())
    assert len(session.exec(select(ProblemAsset)).all()) == 2
    assert len(session.exec(select(ProblemTestCase)).all()) == 1

    downloaded = client.get(
        f"{base}/assets/{testcase['input_asset_id']}/download", headers=headers
    )
    assert downloaded.status_code == 200
    assert downloaded.content == b"1 2\n"

    updated = client.patch(
        f"{base}/testcases/{testcase['id']}",
        json={"score": 50, "case_name": "renamed"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["score"] == 50

    deleted = client.delete(f"{base}/testcases/{testcase['id']}", headers=headers)
    assert deleted.status_code == 204
    assert session.exec(select(ProblemTestCase)).all() == []
    assert session.exec(select(ProblemAsset)).all() == []


def test_published_revision_rejects_testcase_changes(
    client,
    create_user,
    login_user,
    auth_headers,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("COURSE_BUNDLE_ROOT", str(tmp_path / "course"))
    problem, revision, headers = _draft_problem(
        client, create_user, login_user, auth_headers
    )
    base = f"/api/admin/problems/{problem['id']}/revisions/{revision['id']}"
    client.post(f"{base}/validate", headers=headers)
    client.post(f"{base}/publish", headers=headers)

    response = client.post(
        f"{base}/testcases",
        data={"case_name": "late", "position": 1},
        files={
            "input_file": ("late.in", b"", "text/plain"),
            "output_file": ("late.out", b"", "text/plain"),
        },
        headers=headers,
    )

    assert response.status_code == 409
