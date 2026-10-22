import io


def test_upload_resume_unauthorized(client, sample_docx_bytes):
    response = client.post(
        "/api/v1/resume/upload",
        files={"file": ("resume.docx", sample_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert response.status_code == 401


def test_upload_unsupported_file_type(client, auth_headers):
    fake_txt = io.BytesIO(b"Hello this is just a text file")
    response = client.post(
        "/api/v1/resume/upload",
        headers=auth_headers,
        files={"file": ("malicious.exe", fake_txt, "application/octet-stream")}
    )
    assert response.status_code == 400
    assert "unsupported file format" in response.json()["detail"].lower()


def test_upload_valid_docx_and_parse(client, auth_headers, sample_docx_bytes):
    response = client.post(
        "/api/v1/resume/upload",
        headers=auth_headers,
        files={"file": ("my_resume.docx", sample_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "resume" in data
    assert data["resume"]["original_filename"] == "my_resume.docx"
    assert data["resume"]["is_active"] is True
    
    parsed = data["parsed_profile"]
    assert parsed is not None
    assert parsed["full_name"] == "Alex Morgan"
    assert "alex.morgan@example.com" in parsed["email"]
    assert "Python" in parsed["skills"]
    assert "React" in parsed["skills"]


def test_get_current_resume(client, auth_headers, sample_docx_bytes):
    # First upload
    client.post(
        "/api/v1/resume/upload",
        headers=auth_headers,
        files={"file": ("my_resume.docx", sample_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )

    # Then retrieve
    response = client.get("/api/v1/resume", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["original_filename"] == "my_resume.docx"


def test_download_resume(client, auth_headers, sample_docx_bytes):
    # Upload
    client.post(
        "/api/v1/resume/upload",
        headers=auth_headers,
        files={"file": ("my_resume.docx", sample_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )

    # Download
    response = client.get("/api/v1/resume/download", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.content) > 0


def test_delete_resume(client, auth_headers, sample_docx_bytes):
    # Upload
    client.post(
        "/api/v1/resume/upload",
        headers=auth_headers,
        files={"file": ("my_resume.docx", sample_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )

    # Delete
    del_resp = client.delete("/api/v1/resume", headers=auth_headers)
    assert del_resp.status_code == 200

    # Verify no active resume
    get_resp = client.get("/api/v1/resume", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json() is None
