def test_http_error_has_request_id_envelope(client):
    response = client.get(
        "/api/homework/999999",
        headers={"X-Request-ID": "test-request-id"},
    )
    payload = response.json()
    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == "test-request-id"
    assert payload["code"] == "http_404"
    assert payload["request_id"] == "test-request-id"
    assert payload["field_errors"] == []


def test_validation_error_has_field_errors(client):
    response = client.post("/api/auth/login", json={"id": 123})
    payload = response.json()
    assert response.status_code == 422
    assert payload["code"] == "validation_error"
    assert payload["field_errors"]
    assert payload["request_id"] == response.headers["X-Request-ID"]
