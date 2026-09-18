from __future__ import annotations

import threading
from dataclasses import dataclass
from html import escape

import qrcode
import qrcode.image.svg
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse


@dataclass
class QRPageState:
    qrcode_url: str
    verify_status: str = "PENDING"
    message: str = "等待扫码认证"


@dataclass
class QRServerHandle:
    thread: threading.Thread
    server: uvicorn.Server


def make_svg(qrcode_url: str) -> str:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=2,
    )
    qr.add_data(qrcode_url)
    qr.make(fit=True)
    image = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
    return image.to_string().decode("utf-8")


def create_app(state: QRPageState) -> FastAPI:
    app = FastAPI(title="Integration Harness QR Page")

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/qr")

    @app.get("/qr", response_class=HTMLResponse)
    def qr_page() -> str:
        svg = make_svg(state.qrcode_url)
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>微信认证二维码</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#f5f7fa; display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }}
    main {{ background:#fff; border-radius:16px; padding:32px; box-shadow:0 10px 30px rgba(0,0,0,.08); max-width:560px; width:90%; text-align:center; }}
    .status {{ margin:18px 0 8px; font-size:20px; font-weight:600; }}
    .pending {{ color:#b7791f; }}
    .verified {{ color:#276749; }}
    .message {{ color:#4a5568; line-height:1.6; }}
    svg {{ max-width:100%; height:auto; }}
  </style>
</head>
<body>
  <main>
    <h1>微信认证二维码</h1>
    {svg}
    <div id="status" class="status pending">等待扫码认证</div>
    <div id="message" class="message">请使用手机微信扫描上方二维码。</div>
    <p class="message">本页面每 3 秒自动查询认证结果。</p>
  </main>
  <script>
    async function poll() {{
      try {{
        const res = await fetch('/state');
        const data = await res.json();
        const status = document.getElementById('status');
        const message = document.getElementById('message');
        if (data.verify_status === 'VERIFIED') {{
          status.textContent = '已验证';
          status.className = 'status verified';
          message.textContent = '认证成功，可以继续恢复学习。';
        }} else {{
          status.textContent = data.message || '等待扫码认证';
          status.className = 'status pending';
          message.textContent = '请使用手机微信扫描上方二维码。';
        }}
      }} catch (err) {{
        console.error(err);
      }}
    }}
    setInterval(poll, 3000);
    poll();
  </script>
</body>
</html>"""

    @app.get("/state", response_class=JSONResponse)
    def state_endpoint() -> dict[str, str]:
        return {
            "qrcode_url": state.qrcode_url,
            "verify_status": state.verify_status,
            "message": state.message,
        }

    @app.get("/health", response_class=JSONResponse)
    def health_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    return app


def start_qr_server(
    state: QRPageState,
    port: int,
    ready_event: threading.Event,
) -> QRServerHandle:
    app = create_app(state)
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="error",
        access_log=False,
    )
    server = uvicorn.Server(config)

    def run() -> None:
        ready_event.set()
        server.run()

    thread = threading.Thread(target=run, name="qr-page-server", daemon=True)
    thread.start()
    return QRServerHandle(thread=thread, server=server)
