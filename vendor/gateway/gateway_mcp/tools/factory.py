import json

from mcp.types import ToolAnnotations

from gateway_mcp.config import read_json, tools_file
from gateway_mcp.services.factory_projects import (
    discover_factory_projects,
    get_factory_runtime_config,
    resolve_factory_project_by_issue,
)
from gateway_mcp.tools.runtime import ToolRun


def register_factory_tools(mcp):
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Gateway Factory Projects Discover", readOnlyHint=True
        )
    )
    async def gateway_factory_projects_discover(
        query: str = "", limit: int = 20
    ) -> str:
        """Discover projects that can be onboarded or executed by the autonomous development factory."""
        tool = "gateway_factory_projects_discover"
        scope = "factory:read"
        run = ToolRun.start(
            tool=tool,
            system="factory",
            scope=scope,
            arguments={"query": query, "limit": limit},
        )
        try:
            actor = run.require_scope()
            result = await discover_factory_projects(
                actor=actor,
                tools_registry=read_json(tools_file(), {"tools": []}),
                query=query,
                limit=limit,
            )
            run.finish()
            return json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2)
        except PermissionError as exc:
            run.denied(exc)
            raise
        except Exception as exc:
            run.error(exc)
            raise

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Gateway Factory Resolve By Issue", readOnlyHint=True
        )
    )
    async def gateway_factory_project_resolve_by_issue(
        issue_id: str,
        allow_queue_fallback: bool = False,
    ) -> str:
        """Resolve one Tracker issue to a factory runtime project config."""
        tool = "gateway_factory_project_resolve_by_issue"
        scope = "factory:read"
        run = ToolRun.start(
            tool=tool,
            system="factory",
            scope=scope,
            arguments={
                "issue_id": issue_id,
                "allow_queue_fallback": allow_queue_fallback,
            },
        )
        try:
            actor = run.require_scope()
            result = await resolve_factory_project_by_issue(
                actor=actor,
                tools_registry=read_json(tools_file(), {"tools": []}),
                issue_id=issue_id,
                allow_queue_fallback=allow_queue_fallback,
            )
            run.finish()
            return json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2)
        except PermissionError as exc:
            run.denied(exc)
            raise
        except Exception as exc:
            run.error(exc)
            raise

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Gateway Factory Runtime Config", readOnlyHint=True
        )
    )
    async def gateway_factory_project_get_runtime_config(
        issue_id: str = "",
        work_id: str = "",
        project_id: str = "",
        tracker_queue: str = "",
        allow_queue_fallback: bool = False,
    ) -> str:
        """Return normalized factory runtime config; prefer work_id for queued Work Contracts."""
        tool = "gateway_factory_project_get_runtime_config"
        scope = "factory:read"
        run = ToolRun.start(
            tool=tool,
            system="factory",
            scope=scope,
            arguments={
                "issue_id": issue_id,
                "work_id": work_id,
                "project_id": project_id,
                "tracker_queue": tracker_queue,
                "allow_queue_fallback": allow_queue_fallback,
            },
        )
        try:
            actor = run.require_scope()
            result = await get_factory_runtime_config(
                actor=actor,
                tools_registry=read_json(tools_file(), {"tools": []}),
                issue_id=issue_id,
                work_id=work_id,
                project_id=project_id,
                tracker_queue=tracker_queue,
                allow_queue_fallback=allow_queue_fallback,
            )
            run.finish()
            return json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2)
        except PermissionError as exc:
            run.denied(exc)
            raise
        except Exception as exc:
            run.error(exc)
            raise
