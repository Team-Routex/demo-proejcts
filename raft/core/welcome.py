"""
raft.core.welcome
~~~~~~~~~~~~~~~~~

Starter landing page shown when DEBUG is on and the app has no HTTP routes
registered yet — similar in spirit to Django's default setup page, with a
Raft-specific design.
"""

from __future__ import annotations

from raft.core.response import RawResponse

# Relaxed CSP for this page only (Google Fonts + inline CSS/JS).
_WELCOME_CSP = (
    "default-src 'none'; "
    "style-src 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "script-src 'unsafe-inline'; "
    "base-uri 'none'; "
    "frame-ancestors 'none'"
)

_WELCOME_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Raft — You're underway</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=Figtree:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>
    :root {
      --ink: #071410;
      --moss: #0f2e24;
      --foam: #d7efe4;
      --mist: #8fb9a8;
      --ember: #e8a35c;
      --ember-hot: #ffc078;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    html, body {
      min-height: 100%;
    }

    body {
      font-family: "Figtree", sans-serif;
      color: var(--foam);
      background: var(--ink);
      overflow-x: hidden;
    }

    .sky {
      position: fixed;
      inset: 0;
      z-index: 0;
      background:
        radial-gradient(ellipse 90% 70% at 12% 18%, rgba(46, 120, 92, 0.45), transparent 55%),
        radial-gradient(ellipse 70% 60% at 88% 12%, rgba(232, 163, 92, 0.18), transparent 50%),
        radial-gradient(ellipse 80% 50% at 55% 100%, rgba(20, 70, 55, 0.55), transparent 55%),
        linear-gradient(165deg, #050d0a 0%, #0b1f18 42%, #102820 100%);
      animation: drift 18s ease-in-out infinite alternate;
    }

    .sky::after {
      content: "";
      position: absolute;
      inset: 0;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.45'/%3E%3C/svg%3E");
      opacity: 0.07;
      pointer-events: none;
      mix-blend-mode: soft-light;
    }

    @keyframes drift {
      from { filter: hue-rotate(0deg); }
      to { filter: hue-rotate(12deg); }
    }

    .wake {
      position: fixed;
      left: -10%;
      right: -10%;
      bottom: 8%;
      height: 2px;
      z-index: 1;
      background: linear-gradient(90deg, transparent, rgba(215, 239, 228, 0.35), transparent);
      animation: wake 4.5s ease-in-out infinite;
    }

    @keyframes wake {
      0%, 100% { opacity: 0.25; transform: scaleX(0.85); }
      50% { opacity: 0.7; transform: scaleX(1); }
    }

    main {
      position: relative;
      z-index: 2;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      justify-content: center;
      padding: clamp(2rem, 6vw, 4.5rem);
      max-width: 52rem;
    }

    .brand {
      font-family: "Bricolage Grotesque", sans-serif;
      font-size: clamp(3.4rem, 12vw, 6.5rem);
      font-weight: 700;
      letter-spacing: -0.04em;
      line-height: 0.92;
      color: var(--foam);
      opacity: 0;
      animation: rise 0.9s cubic-bezier(0.22, 1, 0.36, 1) 0.1s forwards;
    }

    .brand span {
      color: var(--ember);
    }

    h1 {
      font-family: "Bricolage Grotesque", sans-serif;
      font-size: clamp(1.35rem, 3.2vw, 1.85rem);
      font-weight: 500;
      letter-spacing: -0.02em;
      margin-top: 1.35rem;
      max-width: 22ch;
      opacity: 0;
      animation: rise 0.9s cubic-bezier(0.22, 1, 0.36, 1) 0.28s forwards;
    }

    .lede {
      margin-top: 1rem;
      font-size: 1.05rem;
      line-height: 1.55;
      color: var(--mist);
      max-width: 36ch;
      opacity: 0;
      animation: rise 0.9s cubic-bezier(0.22, 1, 0.36, 1) 0.42s forwards;
    }

    .next {
      margin-top: 2.75rem;
      opacity: 0;
      animation: rise 0.9s cubic-bezier(0.22, 1, 0.36, 1) 0.58s forwards;
    }

    .next p {
      font-size: 0.8rem;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--ember-hot);
      margin-bottom: 0.75rem;
    }

    pre {
      font-family: ui-monospace, "Cascadia Code", "Segoe UI Mono", monospace;
      font-size: 0.82rem;
      line-height: 1.55;
      color: var(--foam);
      background: rgba(7, 20, 16, 0.55);
      border-left: 3px solid var(--ember);
      padding: 1rem 1.15rem;
      overflow-x: auto;
      white-space: pre;
    }

    footer {
      margin-top: 3rem;
      font-size: 0.85rem;
      color: var(--mist);
      opacity: 0;
      animation: rise 0.9s cubic-bezier(0.22, 1, 0.36, 1) 0.72s forwards;
    }

    footer strong { color: var(--foam); font-weight: 600; }

    @keyframes rise {
      from { opacity: 0; transform: translateY(1.25rem); }
      to { opacity: 1; transform: translateY(0); }
    }

    @media (prefers-reduced-motion: reduce) {
      .sky, .wake, .brand, h1, .lede, .next, footer {
        animation: none !important;
        opacity: 1 !important;
        transform: none !important;
        filter: none !important;
      }
    }
  </style>
</head>
<body>
  <div class="sky" aria-hidden="true"></div>
  <div class="wake" aria-hidden="true"></div>
  <main>
    <p class="brand">Ra<span>ft</span></p>
    <h1>The current is clear. Your first route will chart the course.</h1>
    <p class="lede">
      This starter page appears only while DEBUG is on and no HTTP routes
      are registered. Define a route and it disappears.
    </p>
    <div class="next">
      <p>Cast off</p>
      <pre>from raft import Raft, Response

app = Raft()

@app.get("/")
async def home(request):
    return Response.success(message="Hello from Raft!")</pre>
    </div>
    <footer>
      Running in <strong>debug</strong> · add <code>routes</code> or
      <code>@app.get</code> to replace this page
    </footer>
  </main>
</body>
</html>
"""


def welcome_response() -> RawResponse:
    """Return the Raft starter HTML page."""
    return RawResponse(
        body=_WELCOME_HTML.encode("utf-8"),
        status_code=200,
        content_type="text/html; charset=utf-8",
        headers={"Content-Security-Policy": _WELCOME_CSP},
    )


def should_show_welcome(*, debug: bool, route_count: int) -> bool:
    """True when the starter page should be served instead of a JSON 404."""
    return bool(debug) and route_count == 0
