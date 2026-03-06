"""
raft.openapi.ui
~~~~~~~~~~~~~~~

HTML page generators for Swagger UI and ReDoc.

Both pages load assets from a public CDN so no extra Python packages are
needed — only a browser and internet access (or a local CDN mirror for
air-gapped environments).
"""

from __future__ import annotations


def swagger_ui_html(openapi_url: str, title: str) -> str:
    """Return a complete Swagger UI HTML page.

    Parameters:
        openapi_url: URL path to the ``/openapi.json`` endpoint.
        title: Page title shown in the browser tab.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — Swagger UI</title>
    <link rel="stylesheet" type="text/css"
          href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css">
    <style>
        html {{ box-sizing: border-box; overflow-y: scroll; }}
        *, *::before, *::after {{ box-sizing: inherit; }}
        body {{ margin: 0; background: #fafafa; }}
        .topbar {{ display: none; }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>

    <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js"
            charset="UTF-8"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-standalone-preset.js"
            charset="UTF-8"></script>
    <script>
        window.onload = function () {{
            window.ui = SwaggerUIBundle({{
                url: "{openapi_url}",
                dom_id: "#swagger-ui",
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset,
                ],
                plugins: [SwaggerUIBundle.plugins.DownloadUrl],
                layout: "BaseLayout",
                deepLinking: true,
                showExtensions: true,
                showCommonExtensions: true,
                defaultModelsExpandDepth: 2,
                defaultModelExpandDepth: 2,
            }});
        }};
    </script>
</body>
</html>"""


def redoc_html(openapi_url: str, title: str) -> str:
    """Return a complete ReDoc HTML page.

    Parameters:
        openapi_url: URL path to the ``/openapi.json`` endpoint.
        title: Page title shown in the browser tab.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — ReDoc</title>
    <style>
        body {{ margin: 0; padding: 0; }}
    </style>
</head>
<body>
    <redoc spec-url="{openapi_url}"
           expand-responses="200,201"
           hide-download-button="false">
    </redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js">
    </script>
</body>
</html>"""
