"""Tests for consistent template rendering across preview and send."""


def test_plain_text_template_preserves_paragraphs_and_line_breaks(isolated_data_dir):
    from connectra_core.template_renderer import render_template_body

    body = "Happy Diwali\n\nWarm Regards,\nYour Company"

    html = render_template_body(body)

    assert html == "<p>Happy Diwali</p><p>Warm Regards,<br>Your Company</p>"


def test_existing_html_template_is_preserved(isolated_data_dir):
    from connectra_core.template_renderer import render_template_body

    body = "<h1>Happy Diwali</h1><p>Warm Regards,<br><strong>Team</strong></p>"

    assert render_template_body(body) == body


def test_explicit_html_body_wins_over_plain_text(isolated_data_dir):
    from connectra_core.template_renderer import render_template_html

    html = render_template_html(
        plain_body="Plain greeting",
        html_body="<h1>HTML greeting</h1>",
    )

    assert html == "<h1>HTML greeting</h1>"


def test_sync_templates_refreshes_updated_admin_template(monkeypatch, isolated_data_dir):
    import json
    import importlib

    from connectra_core import config
    import connectra_core.template_sync as template_sync

    admin_templates = isolated_data_dir / "admin_templates"
    admin_templates.mkdir()
    runtime_template = config.TEMPLATE_DIR / "Greeting.json"
    admin_template = admin_templates / "Greeting.json"

    config.TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    runtime_template.write_text(
        json.dumps({"name": "Greeting", "subject": "Old", "body": "Old body"}),
        encoding="utf-8",
    )
    admin_template.write_text(
        json.dumps({"name": "Greeting", "subject": "New", "body": "New body"}),
        encoding="utf-8",
    )

    template_sync = importlib.reload(template_sync)
    monkeypatch.setattr(template_sync, "_source_template_dirs", lambda: [admin_templates])

    template_sync.sync_templates()

    synced = json.loads(runtime_template.read_text(encoding="utf-8"))
    assert synced["subject"] == "New"
    assert synced["body"] == "New body"


def test_sync_templates_leaves_runtime_empty_without_sources(monkeypatch, isolated_data_dir):
    import importlib

    import connectra_core.template_sync as template_sync
    from connectra_core import config

    template_sync = importlib.reload(template_sync)
    monkeypatch.setattr(template_sync, "_source_template_dirs", lambda: [])

    template_sync.sync_templates()

    assert list(config.TEMPLATE_DIR.glob("*.json")) == []
