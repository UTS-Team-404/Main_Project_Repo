from pathlib import Path
from flask import Flask, render_template_string, request
import pandas as pd

#  we can add the csv file that we get from the rapberry pi "sample_scan.csv to team_scan.csv"
CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_scan.csv"

app = Flask(__name__)

def load_df():
    df = pd.read_csv(CSV_PATH)
    return df

TEMPLATE = """
<!doctype html>
<title>Wi‑Fi Intel</title>
<h2>SSIDs Observed</h2>
<form method="get">
  <input name="q" placeholder="filter by SSID" value="{{q or ''}}">
  <button>Search</button>
</form>
<ul>
{% for ssid, cnt in ssids %}
  <li><a href="/ssid/{{ssid|e}}">{{ssid or '(hidden)'}} ({{cnt}} frames)</a></li>
{% endfor %}
</ul>
<hr>
{% if macs is not none %}
  <h3>MACs for SSID: {{selected or '(hidden)'}} </h3>
  <table border="1" cellpadding="4">
    <tr><th>MAC (BSSID)</th><th>Frames</th><th>First</th><th>Last</th><th>Channels</th><th>Min/Avg/Max RSSI</th></tr>
    {% for r in macs %}
      <tr>
        <td>{{r['bssid']}}</td>
        <td>{{r['frames']}}</td>
        <td>{{r['first_seen']}}</td>
        <td>{{r['last_seen']}}</td>
        <td>{{r['channels']}}</td>
        <td>{{r['min_rssi']}} / {{r['avg_rssi']}} / {{r['max_rssi']}}</td>
      </tr>
    {% endfor %}
  </table>
{% endif %}
"""

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    df = load_df()
    if q:
        df = df[df["ssid"].fillna("").str.contains(q, case=False, na=False)]
    ssid_counts = df.groupby("ssid").size().sort_values(ascending=False)
    ssids = list(ssid_counts.items())
    return render_template_string(TEMPLATE, ssids=ssids, macs=None, selected=None, q=q)

@app.route("/ssid/<ssid>")
def ssid_view(ssid):
    df = load_df()
    df = df[df["ssid"].fillna("") == ssid]
    g = df.groupby("bssid")
    agg = g.agg(frames=("bssid","size"),
                first_seen=("timestamp","min"),
                last_seen=("timestamp","max"),
                min_rssi=("rssi","min"),
                avg_rssi=("rssi","mean"),
                max_rssi=("rssi","max"),
                channels=("channel", lambda s: ", ".join(sorted(set(s.astype(str))))))
    rows = []
    for mac, r in agg.sort_values("frames", ascending=False).iterrows():
        rows.append({
            "bssid": mac,
            "frames": int(r["frames"]),
            "first_seen": r["first_seen"],
            "last_seen": r["last_seen"],
            "channels": r["channels"],
            "min_rssi": r["min_rssi"],
            "avg_rssi": round(r["avg_rssi"],1) if pd.notna(r["avg_rssi"]) else "",
            "max_rssi": r["max_rssi"],
        })
    ssid_counts = df.groupby("ssid").size().sort_values(ascending=False)
    ssids = list(ssid_counts.items())
    return render_template_string(TEMPLATE, ssids=ssids, macs=rows, selected=ssid, q=None)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
