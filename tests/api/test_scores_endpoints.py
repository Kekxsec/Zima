import pytest
from httpx import AsyncClient

from tests.factories import ScoreFactory


@pytest.mark.asyncio
async def test_get_identity_score_history_returns_200(
    auth_client: AsyncClient,
    db_session,
) -> None:
    user = auth_client.test_user  # type: ignore[attr-defined]
    db_session.add(
        ScoreFactory.build(
            user_id=user.id,
            domain="identity",
            score=72,
            signal_count=4,
        )
    )
    await db_session.commit()

    response = await auth_client.get("/api/v1/scores/identity/history")
    assert response.status_code == 200
    body = response.json()
    assert body["domain"] == "identity"
    assert len(body["history"]) == 1
