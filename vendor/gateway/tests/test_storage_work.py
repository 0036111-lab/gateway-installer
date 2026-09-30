import unittest
from unittest.mock import MagicMock, patch

from support import install_dependency_stubs

install_dependency_stubs()

from gateway_mcp.services.storage_work import append_work_event_locked, work_metrics


class StorageWorkTests(unittest.TestCase):
    def test_artifact_append_locks_work_before_reading_latest_event(self) -> None:
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.side_effect = [
            {"work_id": "work-1", "project_id": "demo"},
            {"payload": {"sequence": 1, "digest": "a" * 64}},
            {"id": 2, "work_id": "work-1", "event_type": "artifact_manifest"},
        ]
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value = cursor

        with (
            patch("gateway_mcp.services.storage_work._require_postgres"),
            patch("gateway_mcp.services.storage_work.ensure_schema"),
            patch(
                "gateway_mcp.services.storage_work._connect", return_value=connection
            ),
        ):
            work, event = append_work_event_locked(
                work_id="work-1",
                actor_subject="service:factory",
                event_type="artifact_manifest",
                payload_factory=lambda latest: {"sequence": latest["sequence"] + 1},
            )

        statements = [
            str(call.args[0]).casefold() for call in cursor.execute.call_args_list
        ]
        self.assertIn("for update", statements[0])
        self.assertIn("order by id desc", statements[1])
        self.assertEqual(work["work_id"], "work-1")
        self.assertEqual(event["id"], 2)
        connection.commit.assert_called_once_with()

    def test_work_metrics_returns_blocked_rate_and_median_corrections(self) -> None:
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = [
            {
                "execution_mode": "factory",
                "runs": 4,
                "accepted_runs": 2,
                "blocked_runs": 1,
                "blocked_rate": 0.25,
                "avg_correction_rounds": 1.5,
                "p50_correction_rounds": 1.0,
            }
        ]
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value = cursor

        with (
            patch("gateway_mcp.services.storage_work._require_postgres"),
            patch("gateway_mcp.services.storage_work.ensure_schema"),
            patch(
                "gateway_mcp.services.storage_work._connect", return_value=connection
            ),
        ):
            rows = work_metrics(project_id="demo", days=30)

        statement, params = cursor.execute.call_args.args
        normalized_statement = " ".join(statement.split()).casefold()
        self.assertIn("as blocked_rate", normalized_statement)
        self.assertIn("order by correction_rounds", normalized_statement)
        self.assertIn("as p50_correction_rounds", normalized_statement)
        self.assertIn("avg(correction_rounds)", normalized_statement)
        self.assertEqual(params, [30, "demo", "demo", "demo", "demo"])
        self.assertEqual(rows[0]["blocked_rate"], 0.25)
        self.assertEqual(rows[0]["avg_correction_rounds"], 1.5)
        self.assertEqual(rows[0]["p50_correction_rounds"], 1.0)


if __name__ == "__main__":
    unittest.main()
