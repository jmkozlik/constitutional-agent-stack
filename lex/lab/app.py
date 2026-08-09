"""The lab server: FastAPI over the read layer, serving one page.

Local only. It reads the repo and returns what it read; nothing here
mutates the harness, and nothing leaves the machine (docs/lab-brief.md,
TECH CONSTRAINTS).

The citation law's second half — *"clicking goes there"* — is `/api/file`,
which is the one route that can reach arbitrary paths. It is confined to
the repo by resolution, not by string inspection, and
`tests/test_lab_app.py` plants a traversal to prove it.
"""

from pathlib import Path

from lab import reader

MAX_FILE_BYTES = 400_000
STATIC = Path(__file__).parent / "static"


def create_app(repo="."):
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles

    root = Path(repo).resolve()
    app = FastAPI(title="lex lab", docs_url=None, redoc_url=None)
    app.state.repo = root

    @app.get("/api/status")
    def status():
        return reader.status(root)

    @app.get("/api/plan-hash")
    def plan_hash():
        return reader.plan_hash(root)

    @app.get("/api/runs")
    def runs():
        rows = reader.runs(root)
        return {"rows": rows,
                "empty_reason": reader.runs_empty_reason(root) if not rows
                                else None}

    @app.get("/api/runs/{dispatch_id}")
    def run_detail(dispatch_id: str):
        try:
            return reader.run_detail(root, dispatch_id)
        except reader.ReaderError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/file")
    def file(path: str = Query(...)):
        target = (root / path).resolve()
        # Confinement by resolution: a "../" that escapes the repo simply is
        # not under root once resolved, whatever it looked like as a string.
        if not target.is_relative_to(root) or not target.is_file():
            raise HTTPException(status_code=404, detail=f"not in repo: {path}")
        data = target.read_bytes()[:MAX_FILE_BYTES]
        try:
            text = data.decode()
        except UnicodeDecodeError:
            raise HTTPException(status_code=415,
                                detail=f"{path} is not text") from None
        return JSONResponse({
            "path": str(target.relative_to(root)),
            "text": text,
            "truncated": target.stat().st_size > MAX_FILE_BYTES,
        })

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


def serve(repo=".", host="127.0.0.1", port=7717, open_browser=True) -> int:
    import uvicorn

    url = f"http://{host}:{port}/"
    if open_browser:
        import threading
        import webbrowser

        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    print(f"lex lab — {Path(repo).resolve()}\n  {url}   (ctrl-c to stop)")
    uvicorn.run(create_app(repo), host=host, port=port, log_level="warning")
    return 0
