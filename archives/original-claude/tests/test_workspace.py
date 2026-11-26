"""API regression checks for project lifecycle, material validation and public job import."""
import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

import server
from coach.errors import CoachError
from coach.job_links import extract, target

RESUME = "Built an interactive dashboard to explore a public dataset for a university project."
JD = "Required: build and document dashboards. Preferred: experience with SQL."
MATERIALS = {"name": "Autumn application", "role": "Product Analyst", "resume": RESUME, "jd": JD}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    return TestClient(server.app)


def test_session_lifecycle(client):
    assert client.get("/api/bootstrap").json()["status"]["connection"] == "offline"
    result = client.post("/api/project", json=MATERIALS).json()
    headers = {"X-Project": result["token"]}
    assert client.get("/api/project").status_code == 410
    assert client.get("/api/project", headers=headers).json()["context"] is None
    failed = client.post("/api/action", headers=headers, json={"kind": "match", "version": 0, "language": "en"})
    assert failed.status_code == 400 and "not connected" in failed.json()["errors"]["en"]
    assert client.put("/api/project?version=0", headers=headers, json={**MATERIALS, "resume": "short"}).status_code == 400
    assert client.get("/api/project", headers=headers).json()["materials"]["resume"] == RESUME
    assert client.put("/api/project?version=0", headers=headers, json={**MATERIALS, "name": "Revised"}).status_code == 200
    assert client.put("/api/project?version=0", headers=headers, json=MATERIALS).status_code == 409
    assert client.delete("/api/project", headers=headers).status_code == 200
    assert client.get("/api/project", headers=headers).status_code == 410


def test_invalid_materials(client):
    for key, bad in [("role", " "), ("resume", "x"*50), ("jd", ""), ("jd", "12345"*10)]:
        assert client.post("/api/project", json={**MATERIALS, key: bad}).status_code == 400
    pdf = PdfWriter()
    pdf.add_blank_page(100,100)
    data = BytesIO()
    pdf.write(data)
    errors = client.post("/api/pdf", content=data.getvalue()).json()["errors"]
    assert "OCR" in errors["en"] and "掃描件" in errors["zh-TW"]


def test_public_link_extraction():
    html = "<p>Responsibilities</p><p>Design and document dashboard requirements for students.</p>"
    data = {"@graph": [{"@type": "JobPosting", "description": html}]}
    assert extract(('<script type="application/ld+json">'+json.dumps(data)+'</script>').encode()).startswith("Responsibilities")
    assert "Navigation" not in extract(("<nav>Navigation</nav><main>"+html+"</main>").encode())
    with pytest.raises(CoachError):
        extract(b"<main>Sign in to view this vacancy</main>")


def test_link_targets_reject_nonpublic_addresses():
    for url in ["file:///etc/hosts","http://127.0.0.1/","http://[::1]/","https://user@example.com/","http://localhost:8888"]:
        with pytest.raises(CoachError):
            target(url)

