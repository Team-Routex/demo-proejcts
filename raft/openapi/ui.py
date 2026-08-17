"""
raft.openapi.ui
~~~~~~~~~~~~~~~

HTML page generators for Swagger UI and ReDoc (CDN assets).
"""

from __future__ import annotations

import html as html_lib


def swagger_ui_html(openapi_url: str, title: str) -> str:
    """Return a complete Swagger UI HTML page."""
    safe_title = html_lib.escape(title)
    safe_url = html_lib.escape(openapi_url, quote=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title} — Swagger UI</title>
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
                url: "{safe_url}",
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
                withCredentials: true,
                requestInterceptor: function (req) {{
                    req.credentials = "same-origin";
                    return req;
                }},
            }});
        }};
    </script>
</body>
</html>"""


def redoc_html(openapi_url: str, title: str) -> str:
    """Return a complete ReDoc HTML page."""
    safe_title = html_lib.escape(title)
    safe_url = html_lib.escape(openapi_url, quote=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title} — ReDoc</title>
    <style>
        body {{ margin: 0; padding: 0; }}
    </style>
</head>
<body>
    <redoc spec-url="{safe_url}"
           expand-responses="200,201"
           hide-download-button="false">
    </redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2.1.5/bundles/redoc.standalone.js">
    </script>
</body>
</html>"""
