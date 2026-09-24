def test_security_page_embeds_sanitized_public_architecture(client):
    response = client.get("/security")

    assert response.status_code == 200
    assert b"security-architecture-public.svg" in response.data
    assert "Vue publique simplifiée".encode() in response.data
    assert b"10.10." not in response.data
    assert b"192.168." not in response.data


def test_public_architecture_svg_is_accessible_and_sanitized(client):
    response = client.get("/static/diagrams/security-architecture-public.svg")

    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    assert b"<title" in response.data
    assert b"<desc" in response.data
    assert b"role=\"img\"" in response.data
    assert b"10.10." not in response.data
    assert b"192.168." not in response.data
    assert b"5432" not in response.data
    assert b"8000" not in response.data
