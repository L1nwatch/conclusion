from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "conclusion.sqlite3", frontend_dist=None)) as client:
        yield client


def fixture_tree():
    return json.loads((Path(__file__).parent / "fixtures/celpip-decision.json").read_text())


def test_decision_crud_title_filter_and_pagination(client):
    assert client.get("/api/decisions").json() == {"count": 0, "offset": 0, "items": []}
    example = client.post("/api/decisions", json=fixture_tree()).json()
    assert example["rootId"] == "celpip" and len(example["nodes"]) == 15
    assert all(node["decisionId"] == example["id"] for node in example["nodes"])

    new = client.post("/api/decisions", json={"title": "  Second decision  "})
    assert new.status_code == 201
    record = new.json()
    assert len(record["nodes"]) == 1
    assert record["rootId"] == record["nodes"][0]["id"]
    assert record["nodes"][0]["parentId"] is None
    assert record["nodes"][0]["text"] == "Second decision"
    assert record["version"] == 1

    url = f"/api/decisions/{record['id']}"
    updated = client.patch(url, json={
        "expectedVersion": 1, "title": "Straße", "description": "context", "status": "Decided",
    }).json()
    assert updated["version"] == 2
    assert updated["nodes"] == record["nodes"]
    assert updated["createdAt"] == record["createdAt"]
    assert updated["description"] == "context"
    filtered = client.get("/api/decisions", params={"query": "STRASSE", "status": "Decided"}).json()
    assert [item["id"] for item in filtered["items"]] == [record["id"]]
    assert "nodes" not in filtered["items"][0]
    page = client.get("/api/decisions", params={"limit": 1, "offset": 1}).json()
    assert page["count"] == 2 and page["items"][0]["id"] == example["id"]
    assert client.get("/api/decisions", params={"query": "%"}).json()["count"] == 0

    assert client.delete(f"{url}?expectedVersion=1").json()["detail"]["currentVersion"] == 2
    assert client.delete(f"{url}?expectedVersion=2").status_code == 204
    assert client.get(url).status_code == 404
    assert client.get("/api/decisions").json()["count"] == 1


@pytest.mark.parametrize(("nodes", "error"), [
    ([{"id": "a", "text": "root"}, {"id": "b", "text": "root"}], "exactly one root"),
    ([{"id": "a", "text": "root"}, {"id": "a", "text": "duplicate"}], "unique"),
    ([{"id": "a", "text": "root"}, {"id": "b", "text": "orphan", "parentId": "other"}], "Parent node"),
    ([
        {"id": "a", "text": "root"},
        {"id": "b", "text": "cycle", "parentId": "c"},
        {"id": "c", "text": "cycle", "parentId": "b"},
    ], "cycle"),
    ([{"id": "a", "text": "root", "positionX": 15}], "positionY"),
    ([
        {"id": "a", "text": "root"},
        {"id": "b", "text": "child", "parentId": "a", "order": 1},
    ], "consecutive"),
])
def test_invalid_initial_trees_do_not_create_decisions(client, nodes, error):
    response = client.post("/api/decisions", json={"title": "Invalid", "nodes": nodes})
    assert response.status_code == 422
    assert error in response.text
    assert client.get("/api/decisions").json()["count"] == 0


def test_atomic_batch_snapshot_and_version_conflicts(client):
    original = client.post("/api/decisions", json=fixture_tree()).json()
    url = f"/api/decisions/{original['id']}"
    failure = client.patch(f"{url}/tree", json={
        "expectedVersion": 1,
        "operations": [
            {"op": "add", "id": "new", "parentId": "pr", "text": "新条件"},
            {"op": "move", "id": "no-draw", "parentId": "new"},
        ],
    })
    assert failure.status_code == 422 and "cycle" in failure.text
    assert client.get(url).json() == original

    response = client.patch(f"{url}/tree", json={
        "expectedVersion": 1,
        "operations": [
            {"op": "add", "id": "new", "parentId": "draw", "text": "测试分支", "order": 0},
            {"op": "add", "id": "new-child", "parentId": "new", "text": "下一步"},
            {"op": "move", "id": "pr", "parentId": "new", "order": 0},
            {"op": "update", "id": "new", "changes": {
                "description": "sample", "positionX": 250, "positionY": -50, "collapsed": True,
            }},
            {"op": "delete", "id": "mid"},
        ],
    })
    assert response.status_code == 200, response.text
    saved = response.json()
    nodes = {node["id"]: node for node in saved["nodes"]}
    assert saved["version"] == 2 and saved["rootId"] == "celpip"
    assert nodes["new"]["positionX"] == 250 and nodes["new"]["collapsed"]
    assert nodes["pr"]["order"] == 0 and nodes["pr"]["parentId"] == "new"
    assert nodes["new-child"]["order"] == 1 and nodes["travel"]["order"] == 0
    assert not {"mid", "mid-high", "retake", "mid-low", "wait-draw"} & nodes.keys()

    for bad in (
        {"operations": [{"op": "delete", "id": "celpip"}]},
        {"operations": [{"op": "move", "id": "new", "parentId": "another-decision"}]},
        {"nodes": [{"id": "replacement-root", "text": "a"}]},
        {"operations": [{"op": "update", "id": "new", "changes": {"positionY": 42}}]},
    ):
        assert client.patch(f"{url}/tree", json={"expectedVersion": 2, **bad}).status_code == 422
    assert client.get(url).json() == saved
    assert client.patch(url, json={"expectedVersion": 1, "title": "Stale"}).status_code == 409
    assert client.patch(f"{url}/tree", json={
        "expectedVersion": 1, "operations": [{"op": "delete", "id": "new"}],
    }).status_code == 409

    snapshot = [
        {key: value for key, value in node.items() if key not in {"createdAt", "updatedAt", "decisionId"}}
        for node in saved["nodes"]
    ]
    snapshot[0]["text"] = "新的根节点文字"
    replaced = client.patch(f"{url}/tree", json={"expectedVersion": 2, "nodes": snapshot})
    assert replaced.status_code == 200
    assert replaced.json()["nodes"][0]["text"] == "新的根节点文字"
    assert replaced.json()["nodes"][0]["createdAt"] == saved["nodes"][0]["createdAt"]
    assert replaced.json()["nodes"][1] == saved["nodes"][1]


def test_two_writers_cannot_save_the_same_version(client):
    decision = client.post("/api/decisions", json={"title": "Race"}).json()
    url = f"/api/decisions/{decision['id']}"

    def write(text):
        return client.patch(f"{url}/tree", json={
            "expectedVersion": 1, "operations": [{
                "op": "update", "id": decision["rootId"], "changes": {"text": text},
            }],
        })

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(write, ["First writer", "Second writer"]))
    assert sorted(response.status_code for response in responses) == [200, 409]
    assert client.get(url).json()["version"] == 2


def test_deep_tree_can_be_saved_and_deleted_without_recursion_limit(client):
    nodes = [
        {"id": f"node-{i}", "parentId": f"node-{i-1}" if i else None, "text": str(i)}
        for i in range(1250)
    ]
    response = client.post("/api/decisions", json={"title": "Deep tree", "nodes": nodes})
    assert response.status_code == 201
    decision = response.json()
    assert len(decision["nodes"]) == len(nodes)
    response = client.patch(f"/api/decisions/{decision['id']}/tree", json={
        "expectedVersion": 1, "operations": [{"op": "delete", "id": "node-1"}],
    })
    assert response.status_code == 200
    assert len(response.json()["nodes"]) == 1
