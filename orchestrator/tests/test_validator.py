from app.services.validator import extract_cmdlets, strip_quoted_strings, validate_command


def test_strip_quoted_strings():
    cmd = 'Get-Something | Where-Object { $_.Name -eq "=== ACTIVE Global Admins ===" }'
    result = strip_quoted_strings(cmd)
    assert "ACTIVE Global Admins" not in result
    assert "Get-Something" in result
    assert "Where-Object" in result


def test_strip_single_quotes():
    cmd = "Get-Item -Filter 'Set-Password'"
    result = strip_quoted_strings(cmd)
    assert "Set-Password" not in result


def test_extract_cmdlets_ignores_quotes():
    cmd = 'Get-DlpCompliancePolicy | Format-Table "=== ACTIVE Global Admins ==="'
    cmdlets = extract_cmdlets(cmd)
    # Should find Get-DlpCompliancePolicy and Format-Table but NOT Global-Admins or similar
    assert "Get-DlpCompliancePolicy" in cmdlets
    assert "Format-Table" in cmdlets
    # The quoted string should not produce a false match
    assert all("Global" not in c and "Admins" not in c for c in cmdlets)


def test_validate_blocked_verbs():
    is_valid, reason, matched = validate_command("Set-MgUser -UserId 123")
    assert not is_valid
    assert "Set-MgUser" in matched


def test_validate_allowed_commands():
    is_valid, reason, matched = validate_command(
        "Get-DlpCompliancePolicy",
        allowed_commands=["Get-DlpCompliancePolicy", "Get-Label"],
        blocked_verbs=[],
    )
    assert is_valid


def test_validate_command_not_in_allowlist():
    is_valid, reason, matched = validate_command(
        "Get-MgUser",
        allowed_commands=["Get-DlpCompliancePolicy"],
        blocked_verbs=[],
    )
    assert not is_valid
    assert "not in allowlist" in reason


def test_validate_no_cmdlets():
    is_valid, reason, matched = validate_command("echo hello world")
    assert is_valid
    assert reason is None
