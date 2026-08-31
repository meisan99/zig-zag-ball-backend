async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_submit_score_success(client):
    response = await client.post(
        "/leaderboard/scores",
        json={"name": "AAA", "value": 100, "game_mode": "classic"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "AAA"
    assert body["value"] == 100


async def test_submit_score_unknown_game_mode(client):
    response = await client.post(
        "/leaderboard/scores",
        json={"name": "AAA", "value": 100, "game_mode": "nonexistent"},
    )
    assert response.status_code == 404


async def test_submit_score_rejects_profanity(client):
    response = await client.post(
        "/leaderboard/scores",
        json={"name": "fuck", "value": 100, "game_mode": "classic"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Cannot accept vulgar terms"


async def test_submit_score_invalid_payload(client):
    response = await client.post(
        "/leaderboard/scores",
        json={"name": "", "value": 100, "game_mode": "classic"},
    )
    assert response.status_code == 422  # Pydantic: name min_length=1


async def test_get_top_returns_ranked_entries(client):
    await client.post("/leaderboard/scores", json={"name": "LOW", "value": 10, "game_mode": "classic"})
    await client.post("/leaderboard/scores", json={"name": "HIGH", "value": 50, "game_mode": "classic"})

    response = await client.get("/leaderboard/top", params={"mode": "classic", "limit": 10})
    assert response.status_code == 200
    entries = response.json()
    assert [e["name"] for e in entries] == ["HIGH", "LOW"]
    assert entries[0]["rank"] == 1


async def test_get_top_unknown_mode(client):
    response = await client.get("/leaderboard/top", params={"mode": "nonexistent"})
    assert response.status_code == 404


async def test_get_top_respects_limit_query_param(client):
    for i in range(5):
        await client.post(
            "/leaderboard/scores",
            json={"name": f"P{i}", "value": i + 1, "game_mode": "classic"},
        )

    response = await client.get("/leaderboard/top", params={"mode": "classic", "limit": 2})
    assert response.status_code == 200
    assert len(response.json()) == 2
