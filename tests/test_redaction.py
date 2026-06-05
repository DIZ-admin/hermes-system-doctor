from hermes_system_doctor.redaction import redact


def test_redacts_secret_shapes():
    text = "OPENAI_API_KEY=sk-1234567890abcdefghijkl token: ghp_abcdefghijklmnopqrstuvwxyz"
    out = redact(text)
    assert "sk-" not in out
    assert "ghp_" not in out
    assert "[REDACTED]" in out


def test_redacts_chat_ids_by_default():
    out = redact("chat -1001234567890123")
    assert "-100123" not in out
    assert "[REDACTED_ID]" in out
