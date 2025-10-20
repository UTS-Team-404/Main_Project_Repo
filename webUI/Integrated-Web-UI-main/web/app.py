#!/etc/.venv/bin/python3 

# Integrated-Web-UI-main/web/app.py
from pathlib import Path
from flask import Flask, render_template, request, send_file, redirect, url_for, flash

# Aldous’ DB helpers (already in this repo)
from db_utils_web import get_projects, get_ssids, get_macs_by_ssid

# Your professional PDF builder wrapper
from gen_report import generate_wifi_pdf

app = Flask(__name__)
app.secret_key = "dev"   # TODO: set properly

@app.route("/")
def index():
    # filters
    pid = request.args.get("pid") or ""    # project id
    q   = request.args.get("q") or ""      # ssid

    # fill dropdowns
    project_ids = get_projects()
    ssids = get_ssids(pid) if pid else []

    # optional table (only when both pid and q are set)
    macs = get_macs_by_ssid(pid, q) if (pid and q) else None

    return render_template(
        "index.html",
        project_ids=project_ids,
        ssids=ssids,
        selected_pid=pid,
        selected_q=q,
        macs=macs,
    )

@app.route("/download", methods=["GET"])
def download():
    pid = (request.args.get("project_id") or "latest").strip() or "latest"
    try:
        pdf_path = generate_wifi_pdf(pid)        # returns a pathlib.Path
        return send_file(pdf_path, as_attachment=True,
                         download_name=Path(pdf_path).name)
    except Exception as e:
        # show a friendly banner at the top of the page
        flash(f"Report failed: {e}", "danger")
        return redirect(url_for("index"))

@app.route("/heatmap")
def heatmap():
    # if Aldous’ page is a template
    return render_template("heatmap_output.html")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
