from html import escape
from typing import Any

from gateway_mcp.services.policy import GatewayActor, has_scope


def fmt_time(value: Any) -> str:
    raw = str(value or "").strip()
    if len(raw) >= 16 and raw[4] == "-" and raw[7] == "-":
        return f"{raw[8:10]}.{raw[5:7]} {raw[11:16]}"
    return raw or "—"


def empty_row(columns: int, text: str = "Нет данных") -> str:
    return f'<tr><td colspan="{columns}"><div class="empty-note">{escape(text)}</div></td></tr>'


def admin_shell(
    *,
    title: str,
    active: str,
    actor: GatewayActor,
    body: str,
    shell_width: str = "1120px",
    extra_head: str = "",
) -> str:
    is_admin = has_scope(actor, "access:admin")
    nav = _navigation(active=active, is_admin=is_admin)
    home_url = "/admin/integrations" if is_admin else "/notifications"
    return f"""
    <!doctype html>
    <html lang="ru">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{escape(title)} · Gateway Platform Auth</title>
      <style>
        /* Hallmark · pre-emit critique: P5 H5 E4 S5 R5 V4
         * genre: modern-minimal · theme: Quiet · macrostructure: Workbench · nav: N3
         * contrast: pass (46–50) · slop: pass · mobile: pass (36, 59, 61–69)
         */
        :root {{
          color-scheme: light;
          --color-canvas: oklch(97.5% 0.004 255);
          --color-surface: oklch(100% 0 0);
          --color-surface-muted: oklch(96% 0.006 255);
          --color-sidebar: oklch(23% 0.025 260);
          --color-sidebar-muted: oklch(77% 0.015 255);
          --color-ink: oklch(24% 0.018 260);
          --color-ink-soft: oklch(43% 0.018 255);
          --color-muted: oklch(53% 0.018 255);
          --color-border: oklch(89% 0.009 255);
          --color-border-strong: oklch(81% 0.014 255);
          --color-accent: oklch(55% 0.19 260);
          --color-accent-ink: oklch(100% 0 0);
          --color-accent-hover: oklch(48% 0.19 260);
          --color-accent-soft: oklch(95% 0.025 260);
          --color-focus: oklch(50% 0.18 255);
          --color-focus-on-dark: oklch(78% 0.12 255);
          --color-success: oklch(48% 0.12 155);
          --color-success-soft: oklch(96% 0.035 155);
          --color-danger: oklch(50% 0.18 28);
          --color-danger-soft: oklch(96% 0.035 28);
          --color-warning: oklch(54% 0.12 75);
          --color-warning-soft: oklch(96% 0.045 85);
          --font-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          --font-display: "Segoe UI Variable Display", "Aptos Display", var(--font-sans);
          --font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
          --space-1: 4px;
          --space-2: 8px;
          --space-3: 12px;
          --space-4: 16px;
          --space-5: 20px;
          --space-6: 24px;
          --space-8: 32px;
          --space-10: 40px;
          --space-12: 48px;
          --radius-control: 6px;
          --radius-panel: 8px;
          --dur-micro: 120ms;
          --dur-short: 220ms;
          --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
          --z-sticky: 200;
          font-family: var(--font-sans);
          color: var(--color-ink);
          background: var(--color-canvas);
        }}
        * {{ box-sizing: border-box; }}
        [hidden] {{ display: none !important; }}
        html, body {{ min-width: 0; overflow-x: clip; }}
        body {{ margin: 0; background: var(--color-canvas); color: var(--color-ink); }}
        button, input, select {{ font: inherit; }}
        .app-shell {{ min-height: 100vh; display: grid; grid-template-columns: 248px minmax(0, 1fr); }}
        .sidebar {{
          position: sticky;
          top: 0;
          z-index: var(--z-sticky);
          height: 100vh;
          display: flex;
          flex-direction: column;
          padding: var(--space-6) var(--space-4);
          background: var(--color-sidebar);
          color: var(--color-surface);
        }}
        .brand {{ display: grid; gap: 2px; padding: 0 var(--space-3); color: var(--color-surface); text-decoration: none; }}
        .brand-name {{ font-family: var(--font-display); font-size: 17px; font-weight: 650; }}
        .brand-product {{ color: var(--color-sidebar-muted); font-size: 12px; }}
        .nav {{ display: grid; gap: var(--space-5); margin-top: var(--space-10); }}
        .nav-group {{ display: grid; gap: var(--space-1); }}
        .nav-label {{ padding: 0 var(--space-3) var(--space-1); color: var(--color-sidebar-muted); font-size: 11px; font-weight: 650; text-transform: uppercase; }}
        .nav-link {{
          display: flex;
          min-height: 38px;
          align-items: center;
          border-radius: var(--radius-control);
          color: var(--color-sidebar-muted);
          padding: 0 var(--space-3);
          font-size: 14px;
          text-decoration: none;
          transition: background var(--dur-micro) var(--ease-out), color var(--dur-micro) var(--ease-out);
        }}
        .nav-link:hover {{ background: color-mix(in oklch, var(--color-surface) 8%, transparent); color: var(--color-surface); }}
        .nav-link:focus-visible {{ outline: 2px solid var(--color-focus-on-dark); outline-offset: 2px; }}
        .nav-link.active {{ background: color-mix(in oklch, var(--color-surface) 12%, transparent); color: var(--color-surface); font-weight: 600; }}
        .identity {{ display: grid; gap: var(--space-1); margin-top: auto; padding: var(--space-4) var(--space-3) 0; border-top: 1px solid color-mix(in oklch, var(--color-surface) 14%, transparent); }}
        .identity-label {{ color: var(--color-sidebar-muted); font-size: 11px; }}
        .identity-user {{ min-width: 0; overflow-wrap: anywhere; font-size: 13px; font-weight: 600; }}
        .workspace {{ min-width: 0; }}
        .content {{ max-width: {shell_width}; margin: 0 auto; padding: var(--space-10) var(--space-8) 64px; }}
        .stack {{ display: grid; gap: var(--space-6); }}
        .page-head, .panel-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-5); }}
        .page-head {{ padding-bottom: var(--space-2); }}
        h1, h2 {{ margin: 0; min-width: 0; overflow-wrap: anywhere; font-family: var(--font-display); letter-spacing: 0; }}
        h1 {{ font-size: 30px; line-height: 1.15; font-weight: 650; }}
        h2 {{ font-size: 18px; line-height: 1.3; font-weight: 650; }}
        p {{ line-height: 1.55; }}
        .lead {{ max-width: 760px; margin: var(--space-2) 0 0; color: var(--color-ink-soft); }}
        .muted, .description {{ color: var(--color-muted); }}
        .description {{ margin: var(--space-2) 0 0; }}
        .small {{ font-size: 13px; }}
        .panel, .stat, form.audit-filter-grid {{ background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-panel); }}
        .panel {{ padding: var(--space-6); }}
        .wide {{ overflow: hidden; }}
        .stat-grid {{ display: grid; grid-template-columns: repeat(5, minmax(140px, 1fr)); gap: var(--space-3); }}
        .stat {{ padding: var(--space-4); }}
        .stat .k {{ color: var(--color-muted); font-size: 12px; }}
        .stat .v {{ margin: var(--space-2) 0; font-size: 26px; font-weight: 650; }}
        .stat .s {{ color: var(--color-muted); font-size: 12px; }}
        .status {{ display: inline-flex; align-items: center; min-height: 24px; padding: 0 var(--space-2); border-radius: 999px; font-size: 12px; font-weight: 650; white-space: nowrap; }}
        .status.ok {{ background: var(--color-success-soft); color: var(--color-success); }}
        .status.neutral {{ background: var(--color-surface-muted); color: var(--color-muted); }}
        .status.missing {{ background: var(--color-danger-soft); color: var(--color-danger); }}
        .status.warning {{ background: var(--color-warning-soft); color: var(--color-warning); }}
        form {{ margin: 0; }}
        form.audit-filter-grid {{ padding: var(--space-5); display: grid; grid-template-columns: repeat(4, minmax(150px, 1fr)); gap: var(--space-4); }}
        label {{ display: grid; gap: var(--space-2); color: var(--color-ink-soft); font-size: 13px; font-weight: 600; }}
        input, select {{ width: 100%; min-height: 44px; padding: var(--space-2) var(--space-3); border: 1px solid var(--color-border-strong); border-radius: var(--radius-control); background: var(--color-surface); color: var(--color-ink); }}
        input:hover, select:hover {{ border-color: var(--color-muted); }}
        input:focus-visible, select:focus-visible {{ border-color: var(--color-accent); outline: 2px solid var(--color-focus); outline-offset: 1px; }}
        input:disabled, select:disabled {{ background: var(--color-surface-muted); opacity: .55; cursor: not-allowed; }}
        input::placeholder {{ color: var(--color-muted); }}
        .audit-filter-actions {{ display: flex; gap: var(--space-2); align-items: end; }}
        button, .button {{
          display: inline-flex;
          min-height: 44px;
          align-items: center;
          justify-content: center;
          border: 1px solid transparent;
          border-radius: var(--radius-control);
          background: var(--color-accent);
          color: var(--color-accent-ink);
          padding: var(--space-2) var(--space-3);
          font: inherit;
          font-size: 14px;
          font-weight: 600;
          line-height: 1;
          text-decoration: none;
          white-space: nowrap;
          cursor: pointer;
          transition: background var(--dur-micro) var(--ease-out), border-color var(--dur-micro) var(--ease-out), color var(--dur-micro) var(--ease-out);
        }}
        button:hover, .button:hover {{ background: var(--color-accent-hover); }}
        button:active, .button:active {{ background: var(--color-accent-hover); }}
        button:focus-visible, .button:focus-visible {{ outline: 2px solid var(--color-focus); outline-offset: 2px; }}
        button:disabled, .button.disabled {{ opacity: .55; cursor: not-allowed; }}
        button.secondary, .button.secondary {{ border-color: var(--color-border-strong); background: var(--color-surface); color: var(--color-ink-soft); }}
        button.secondary:hover, .button.secondary:hover {{ border-color: var(--color-muted); background: var(--color-surface-muted); color: var(--color-ink); }}
        button.danger, .button.danger {{ border-color: var(--color-danger-soft); background: var(--color-surface); color: var(--color-danger); }}
        button.danger:hover, .button.danger:hover {{ border-color: var(--color-danger); background: var(--color-danger-soft); }}
        .table-wrap {{ overflow-x: auto; margin-top: var(--space-4); }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        th, td {{ padding: 12px 10px; border-bottom: 1px solid var(--color-border); text-align: left; vertical-align: top; }}
        th {{ color: var(--color-muted); font-size: 11px; font-weight: 650; text-transform: uppercase; }}
        tbody tr:last-child td {{ border-bottom: 0; }}
        code {{ font-family: var(--font-mono); font-size: 12px; }}
        .table-sub {{ display: block; color: var(--color-muted); margin-top: var(--space-1); }}
        .audit-badges {{ display: flex; gap: var(--space-1); flex-wrap: wrap; }}
        .audit-pager {{ display: flex; align-items: center; justify-content: flex-end; gap: var(--space-3); margin-top: var(--space-4); }}
        .empty-note {{ padding: var(--space-6); color: var(--color-muted); text-align: center; }}
        .banner {{ padding: var(--space-3) var(--space-4); border: 1px solid var(--color-border); border-radius: var(--radius-control); }}
        .banner.error, .errorbox {{ border-color: var(--color-danger); background: var(--color-danger-soft); color: var(--color-danger); }}
        .banner.ok, .okbox {{ border-color: var(--color-success); background: var(--color-success-soft); color: var(--color-success); }}
        @media (max-width: 1040px) {{ .stat-grid, form.audit-filter-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
        @media (max-width: 900px) {{
          .app-shell {{ display: block; }}
          .sidebar {{ position: static; width: 100%; height: auto; padding: var(--space-4); }}
          .brand {{ padding: 0; }}
          .nav {{ display: flex; width: 100%; gap: var(--space-1); margin-top: var(--space-4); overflow-x: auto; padding-bottom: var(--space-1); }}
          .nav-group {{ display: contents; }}
          .nav-label {{ display: none; }}
          .nav-link {{ flex: 0 0 auto; white-space: nowrap; }}
          .identity {{ margin-top: var(--space-4); padding: var(--space-3) 0 0; }}
          .content {{ padding-top: var(--space-8); }}
        }}
        @media (max-width: 560px) {{
          .nav {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); overflow: visible; }}
          .nav-link {{ width: 100%; min-height: 36px; padding: 0 var(--space-2); font-size: 12px; }}
          .content {{ padding: var(--space-6) var(--space-4) var(--space-10); }}
          .stack {{ gap: var(--space-5); }}
          .page-head {{ display: grid; grid-template-columns: minmax(0, 1fr); }}
          .page-head > button, .page-head > .button {{ width: 100%; }}
          h1 {{ font-size: 26px; }}
          .panel {{ padding: var(--space-5); }}
          .stat-grid, form.audit-filter-grid {{ grid-template-columns: minmax(0, 1fr); }}
          .audit-filter-actions {{ display: grid; grid-template-columns: minmax(0, 1fr); }}
          .audit-filter-actions > * {{ width: 100%; }}
        }}
        @media (prefers-reduced-motion: reduce) {{
          *, *::before, *::after {{ animation-duration: 150ms !important; transition-duration: 150ms !important; }}
        }}
      </style>
      {extra_head}
    </head>
    <body>
      <div class="app-shell">
        <aside class="sidebar">
          <a class="brand" href="{home_url}"><span class="brand-name">Gateway Platform</span><span class="brand-product">MCP Gateway</span></a>
          <nav class="nav" aria-label="Основная навигация">{nav}</nav>
          <div class="identity"><span class="identity-label">Текущая учётная запись</span><span class="identity-user">{escape(actor.display)}</span></div>
        </aside>
        <div class="workspace"><main class="content"><div class="stack">{body}</div></main></div>
      </div>
    </body>
    </html>
    """


def _navigation(*, active: str, is_admin: bool) -> str:
    groups = []
    if is_admin:
        groups.append(
            (
                "Управление",
                (
                    ("integrations", "Интеграции", "/admin/integrations"),
                    ("audit", "Журнал событий", "/admin/audit"),
                    ("telemetry", "Метрики навыков", "/admin/telemetry/skills"),
                ),
            )
        )
    groups.append(
        (
            "Рабочее место",
            (
                ("notifications", "Уведомления", "/notifications"),
                ("credentials", "Мои подключения", "/credentials"),
            ),
        )
    )
    return "".join(
        '<div class="nav-group">'
        f'<div class="nav-label">{escape(label)}</div>'
        + "".join(
            f'<a class="nav-link{" active" if key == active else ""}" href="{href}">{escape(item_label)}</a>'
            for key, item_label, href in items
        )
        + "</div>"
        for label, items in groups
    )
