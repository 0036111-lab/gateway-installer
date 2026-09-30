import json
import tempfile
import unittest
from pathlib import Path

from gateway_installer.cli import _hermes_command
from gateway_installer.core import (
    InstallerError,
    _env_lines,
    _harden_compose,
    _patch_policy,
    normalize_public_url,
    parse_env,
)


class InstallerTests(unittest.TestCase):
    def test_https_required_by_default(self):
        self.assertEqual(normalize_public_url("https://mcp.example.net/"), "https://mcp.example.net")
        with self.assertRaises(InstallerError):
            normalize_public_url("http://mcp.example.net")

    def test_test_http_can_be_explicitly_allowed(self):
        self.assertEqual(
            normalize_public_url("http://127.0.0.1:8000", allow_http=True),
            "http://127.0.0.1:8000",
        )

    def test_generated_env_defaults_to_auth_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(
                _env_lines("https://mcp.example.net"),
                encoding="utf-8",
            )
            env = parse_env(path)
        self.assertEqual(env["GATEWAY_AUTH_ENABLED"], "false")
        self.assertEqual(env["GATEWAY_ALLOWED_EMAIL_DOMAINS"], "gateway.invalid")
        self.assertEqual(env["YANDEX_OAUTH_CLIENT_ID"], "")
        self.assertEqual(env["YANDEX_OAUTH_CLIENT_SECRET"], "")
        self.assertEqual(env["GATEWAY_RESOURCE_URL"], "https://mcp.example.net/mcp")
        self.assertNotIn("change-me", "\n".join(env.values()))

    def test_generated_env_supports_yandex_auth_when_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(
                _env_lines(
                    "https://mcp.example.net",
                    "client-id",
                    "client-secret",
                    auth_enabled=True,
                ),
                encoding="utf-8",
            )
            env = parse_env(path)
        self.assertEqual(env["GATEWAY_AUTH_ENABLED"], "true")
        self.assertEqual(env["YANDEX_OAUTH_CLIENT_ID"], "client-id")
        self.assertEqual(env["YANDEX_OAUTH_CLIENT_SECRET"], "client-secret")
        self.assertEqual(env["YANDEX_OAUTH_SCOPES"], "login:email login:info")

    def test_generated_env_preserves_runtime_secrets(self):
        preserved = {
            "POSTGRES_PASSWORD": "existing-postgres-password",
            "GATEWAY_JWT_SECRET": "existing-jwt-secret",
            "GATEWAY_USER_TOKEN_ENCRYPTION_KEY": "existing-encryption-key",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(
                _env_lines("https://new.example.net", preserved=preserved),
                encoding="utf-8",
            )
            env = parse_env(path)
        self.assertEqual(env["POSTGRES_PASSWORD"], preserved["POSTGRES_PASSWORD"])
        self.assertEqual(env["GATEWAY_JWT_SECRET"], preserved["GATEWAY_JWT_SECRET"])
        self.assertEqual(
            env["GATEWAY_USER_TOKEN_ENCRYPTION_KEY"],
            preserved["GATEWAY_USER_TOKEN_ENCRYPTION_KEY"],
        )
        self.assertEqual(env["GATEWAY_PUBLIC_URL"], "https://new.example.net")

    def test_owner_policy_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gateway-policy.json"
            path.write_text(json.dumps({"allowed_email_domains": [], "users": {}, "groups": {"admins": {"scopes": ["*"]}}}), encoding="utf-8")
            _patch_policy(path, "Owner@Example.Net")
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["allowed_email_domains"], ["gateway.invalid"])
        self.assertEqual(data["users"]["owner@example.net"], {"groups": ["admins"]})

    def test_compose_is_hardened(self):
        original = '''services:\n  gateway:\n    environment:\n      GATEWAY_ALLOWED_EMAIL_DOMAINS: ${GATEWAY_ALLOWED_EMAIL_DOMAINS:-}\n      YONOTE_BASE_URL: ${YONOTE_BASE_URL:-https://wiki.example.com}\n      GITLAB_API_BASE_URL: ${GITLAB_API_BASE_URL:-https://gitlab.example.com/api/v4}\n      YANDEX_OAUTH_CLIENT_ID: ${YANDEX_OAUTH_CLIENT_ID:?set YANDEX_OAUTH_CLIENT_ID}\n      YANDEX_OAUTH_CLIENT_SECRET: ${YANDEX_OAUTH_CLIENT_SECRET:?set YANDEX_OAUTH_CLIENT_SECRET}\n    ports:\n      - "${GATEWAY_PORT:-8000}:8000"\n'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "docker-compose.yml"
            path.write_text(original, encoding="utf-8")
            _harden_compose(path)
            text = path.read_text(encoding="utf-8")
        self.assertIn('"127.0.0.1:${GATEWAY_PORT:-8000}:8000"', text)
        self.assertIn("GATEWAY_ALLOWED_EMAIL_DOMAINS: ${GATEWAY_ALLOWED_EMAIL_DOMAINS:-gateway.invalid}", text)
        self.assertIn("YONOTE_BASE_URL: ${YONOTE_BASE_URL-}", text)
        self.assertIn("GITLAB_API_BASE_URL: ${GITLAB_API_BASE_URL-}", text)
        self.assertIn("YANDEX_OAUTH_CLIENT_ID: ${YANDEX_OAUTH_CLIENT_ID:-}", text)
        self.assertIn("YANDEX_OAUTH_CLIENT_SECRET: ${YANDEX_OAUTH_CLIENT_SECRET:-}", text)

    def test_hermes_adapter_command(self):
        self.assertEqual(
            _hermes_command("https://mcp.example.net/mcp", "gateway"),
            ["hermes", "mcp", "add", "gateway", "--url", "https://mcp.example.net/mcp", "--auth", "oauth"],
        )


if __name__ == "__main__":
    unittest.main()
