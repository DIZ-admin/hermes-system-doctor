from hermes_system_doctor.redaction import redact


def test_redacts_secret_shapes():
    provider_key = "OPENAI" + "_API" + "_KEY=" + "sk" + "-123...ijkl"
    github_token = "gh" + "p_" + "ab...wxyz"
    text = f"{provider_key} token: {github_token}"
    out = redact(text)
    assert "sk-" not in out
    assert "ghp_" not in out
    assert "[REDACTED]" in out


def test_redacts_chat_ids_by_default():
    out = redact("chat -1001234567890123")
    assert "-100123" not in out
    assert "[REDACTED_ID]" in out
