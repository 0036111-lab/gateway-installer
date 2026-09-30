import unittest
from unittest.mock import patch

from support import install_dependency_stubs

install_dependency_stubs()


class FakeCursor:
    def __init__(self, *, row=None, rows=None):
        self.row = row
        self.rows = rows or []
        self.calls = []
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_obj = cursor
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True


class StorageServiceConnectionTests(unittest.TestCase):
    def test_listing_never_requests_or_returns_encrypted_payload(self) -> None:
        from gateway_mcp.services import storage_service_connections

        cursor = FakeCursor(
            rows=[
                {
                    "system": "openrouter",
                    "configured_fields": ["OPENROUTER_API_KEY"],
                    "state": "active",
                    "version": 1,
                }
            ]
        )
        with (
            patch.object(
                storage_service_connections, "postgres_enabled", return_value=True
            ),
            patch.object(storage_service_connections, "ensure_schema"),
            patch.object(
                storage_service_connections,
                "_connect",
                return_value=FakeConnection(cursor),
            ),
        ):
            rows = storage_service_connections.list_service_connections()

        self.assertNotIn("payload", rows[0])
        self.assertNotIn("payload_encrypted", rows[0])
        self.assertNotIn("payload_encrypted", cursor.calls[0][0].casefold())

    def test_payload_is_decrypted_only_for_explicit_runtime_read(self) -> None:
        from gateway_mcp.services import storage_service_connections

        cursor = FakeCursor(
            row={
                "system": "openrouter",
                "payload_encrypted": "ciphertext",
                "state": "active",
            }
        )
        with (
            patch.object(
                storage_service_connections, "postgres_enabled", return_value=True
            ),
            patch.object(storage_service_connections, "ensure_schema"),
            patch.object(
                storage_service_connections,
                "_connect",
                return_value=FakeConnection(cursor),
            ),
            patch.object(
                storage_service_connections,
                "_decrypt_secret",
                return_value='{"OPENROUTER_API_KEY":"secret"}',
            ) as decrypt,
        ):
            row = storage_service_connections.get_service_connection(
                "openrouter", include_payload=True
            )

        decrypt.assert_called_once_with("ciphertext")
        self.assertEqual(row["payload"]["OPENROUTER_API_KEY"], "secret")
        self.assertNotIn("payload_encrypted", row)


if __name__ == "__main__":
    unittest.main()
