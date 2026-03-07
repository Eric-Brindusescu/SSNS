"""
Service for rendering text + dictionary into HTML using Jinja2.
Uses a sandboxed environment to prevent template injection.
"""
from jinja2 import BaseLoader, exceptions, sandbox


def render_html(text: str, variables: dict[str, str]) -> str:
    """
    Render an HTML page with the given text and template variables.

    The text may contain Jinja2 template syntax (e.g., {{ name }}).
    The dictionary values fill those template variables.
    """
    env = sandbox.SandboxedEnvironment(loader=BaseLoader())

    # Render the user's text with their variables
    try:
        text_template = env.from_string(text)
        rendered_text = text_template.render(**variables)
    except exceptions.TemplateSyntaxError as exc:
        raise ValueError(f"Invalid template syntax in text: {exc}") from exc
    except exceptions.UndefinedError as exc:
        raise ValueError(f"Undefined variable in template: {exc}") from exc
    except exceptions.SecurityError as exc:
        raise ValueError(f"Disallowed operation in template: {exc}") from exc

    # Render the full page with the rendered text embedded
    page_template = env.from_string(_PAGE_TEMPLATE)
    return page_template.render(content=rendered_text, variables=variables)


_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rendered Document</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            max-width: 800px;
            margin: 2rem auto;
            padding: 0 1rem;
            line-height: 1.7;
            color: #1a1a2e;
            background: #f0f2f5;
        }
        .content {
            background: white;
            padding: 2.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .variables-section {
            margin-top: 2rem;
        }
        .variables-section h3 {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #6c757d;
            margin-bottom: 0.75rem;
        }
        .variables-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        }
        .variables-table th,
        .variables-table td {
            border: 1px solid #e9ecef;
            padding: 0.6rem 1rem;
            text-align: left;
            font-size: 0.9rem;
        }
        .variables-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }
        .variables-table td:first-child {
            font-family: 'SF Mono', 'Fira Code', monospace;
            color: #6f42c1;
        }
    </style>
</head>
<body>
    <div class="content">{{ content }}</div>
    {% if variables %}
    <div class="variables-section">
        <h3>Template Variables</h3>
        <table class="variables-table">
            <tr><th>Key</th><th>Value</th></tr>
            {% for key, value in variables.items() %}
            <tr><td>{{ key }}</td><td>{{ value }}</td></tr>
            {% endfor %}
        </table>
    </div>
    {% endif %}
</body>
</html>"""
