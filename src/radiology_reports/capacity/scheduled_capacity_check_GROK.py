#!/usr/bin/env python3
"""
scheduled_capacity_check.py
Final working version - keeps original layout + adds network totals + yesterday actual vs scheduled
"""
import argparse
from collections import defaultdict
from datetime import date, timedelta, datetime
import pyodbc
import sys
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# -------------------------
# Configuration
# -------------------------
DEFAULT_WEIGHT = 999.0

SMTP_SERVER = "phimlr1.rrc.center"
SMTP_PORT = 25
SENDER_EMAIL = "dparrish@radiologyregional.com"
DEFAULT_RECIPIENTS = ["dparrish@radiologyregional.com"]

# -------------------------
# DB & Utils
# -------------------------
def get_conn():
    return pyodbc.connect(
        r"DRIVER={ODBC Driver 17 for SQL Server};"
        r"SERVER=phiSQL1.rrc.center;"
        r"DATABASE=RRC_Daily_Report;"
        r"Trusted_Connection=yes;",
        autocommit=True,
    )

def load_current_weights(cursor):
    today = date.today()
    sql = """
        SELECT modality, weight
        FROM dbo.Modality_Weight_Governance
        WHERE effective_start <= ? AND (effective_end IS NULL OR effective_end > ?)
    """
    cursor.execute(sql, (today, today))
    weights = {}
    for row in cursor.fetchall():
        mod_raw = row[0].strip()
        mod_norm = mod_raw.upper().replace(" ", "").replace("-", "")
        weights[mod_norm] = float(row[1])
    return weights

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--start-date", "-s", help="Start DOS (default: today → tomorrow)")
    p.add_argument("--days", "-n", type=int, default=1)
    p.add_argument("--send-email", action="store_true")
    p.add_argument("--recipients", type=str)
    return p.parse_args()

def format_table(rows, headers, max_rows=None):
    output = io.StringIO()
    rows = list(rows)
    if max_rows and len(rows) > max_rows:
        rows = rows[:max_rows]
        omitted = len(rows) - max_rows
    else:
        omitted = 0

    widths = [len(h) for h in headers]
    for row in rows:
        for i, v in enumerate(row):
            widths[i] = max(widths[i], len(str(v)))

    def fmt(r): return "  ".join(str(r[i]).ljust(widths[i]) for i in range(len(headers)))
    print(fmt(headers), file=output)
    print("  ".join("-" * w for w in widths), file=output)
    for row in rows:
        print(fmt(row), file=output)
    if omitted:
        print(f"... ({omitted} more rows omitted) ...", file=output)
    return output.getvalue()

def send_report_email(text, recipients):
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = f"Daily Radiology Capacity Report – Scheduled for Tomorrow ({date.today()})"

    html = f"""
    <html><body style="font-family: Arial;">
    <pre style="font-family: Consolas; font-size: 11pt; line-height: 1.4;">
{text
  .replace("OVER CAPACITY", '<span style="color:#d63031;font-weight:bold;">OVER CAPACITY</span>')
  .replace("AT CAPACITY", '<span style="color:#27ae60;font-weight:bold;">AT CAPACITY</span>')
  .replace("UNDER CAPACITY (GAP)", '<span style="color:#3498db;font-weight:bold;">UNDER CAPACITY (GAP)</span>')
  .replace("UNDER (GAP)", '<span style="color:#3498db;font-weight:bold;">UNDER (GAP)</span>')}
    </pre></body></html>
    """
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.sendmail(SENDER_EMAIL, recipients, msg.as_string())
    print(f"\nEmail sent to: {', '.join(recipients)}")

# -------------------------
# Main
# -------------------------
def main():
    args = parse_args()
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date() if args.start_date else date.today()
    end_date = start_date + timedelta(days=args.days - 1)
    recipients = [e.strip() for e in args.recipients.split(",")] if args.recipients else DEFAULT_RECIPIENTS

    conn = get_conn()
    cursor = conn.cursor()

    WEIGHTS = load_current_weights(cursor)

    # ==================== TOMORROW'S SCHEDULED (unchanged & working) ====================
    cursor.execute("""
        SELECT s.dos, s.location, s.modality, SUM(s.volume) AS volume
        FROM dbo.v_Scheduled_Current s
        JOIN dbo.LOCATIONS l ON s.location = l.LocationName AND ISNULL(l.Active,1)=1
        WHERE s.dos BETWEEN ? AND ?
        GROUP BY s.dos, s.location, s.modality
    """, (start_date, end_date))
    sched_rows = [{c[0].lower(): v for c,v in zip(cursor.description, row)} for row in cursor.fetchall()]

    detail_map = defaultdict(lambda: {"volume":0, "weighted":0.0})
    unknown = set()
    for r in sched_rows:
        dos = r["dos"].date() if isinstance(r["dos"], datetime) else r["dos"]
        loc = r["location"]
        mod = (r["modality"] or "").strip()
        vol = float(r["volume"])
        norm = mod.upper().replace(" ","").replace("-","")
        w = WEIGHTS.get(norm, DEFAULT_WEIGHT)
        if w == DEFAULT_WEIGHT: unknown.add(mod)
        detail_map[(dos, loc, mod)]["volume"] += vol
        detail_map[(dos, loc, mod)]["weighted"] += vol * w

    loc_map = defaultdict(lambda: {"exams":0, "weighted":0.0})
    for (dos,loc,_), v in detail_map.items():
        loc_map[(dos,loc)]["exams"] += v["volume"]
        loc_map[(dos,loc)]["weighted"] += v["weighted"]

    # Capacity
    cursor.execute("SELECT location, capacity_weighted_90th FROM dbo.v_Capacity_Model")
    cap_loc = {r[0]: round(float(r[1]),2) for r in cursor.fetchall()}
    total_capacity = sum(cap_loc.values())

    # Build tomorrow's location output
    loc_output = []
    total_scheduled = 0.0
    for (dos,loc), v in loc_map.items():
        exams = int(v["exams"])
        weighted = round(v["weighted"], 2)
        total_scheduled += weighted
        cap = cap_loc.get(loc)
        pct = round(weighted/cap, 3) if cap else None
        gap = round(cap-weighted, 2) if cap and weighted < cap else None
        status = "NO CAP"
        if cap:
            if weighted > cap*1.05: status = "OVER CAPACITY"
            elif weighted >= cap*0.95: status = "AT CAPACITY"
            else: status = "UNDER CAPACITY (GAP)"
        loc_output.append((dos.isoformat(), loc, exams, weighted, cap, pct, gap, status))

    loc_sorted = sorted(loc_output, key=lambda x: x[5] if x[5] else 0, reverse=True)

    # Modality detail (exactly as before)
    mod_output = []
    for (dos,loc,mod), v in detail_map.items():
        mod_output.append((dos.isoformat(), loc, mod, int(v["volume"]), round(v["weighted"],2), None, None, "NO CAP"))

    # ==================== YESTERDAY ACTUAL vs SCHEDULED ====================
    yesterday = date.today() - timedelta(days=1)
    y_str = yesterday.strftime("%Y-%m-%d")

    # Actual
    cursor.execute("""
        SELECT location, SUM(weighted_units) actual
        FROM dbo.v_Daily_Workload_Weighted w
        JOIN dbo.LOCATIONS l ON w.location=l.LocationName AND ISNULL(l.Active,1)=1
        WHERE dos=?
        GROUP BY location
    """, (y_str,))
    actual_dict = {r[0]: round(float(r[1]),2) for r in cursor.fetchall()}
    total_actual = sum(actual_dict.values())

    # Yesterday's scheduled (morning snapshot)
    cursor.execute("""
        SELECT location, modality, SUM(volume) vol
        FROM dbo.SCHEDULED
        WHERE inserted = dos AND dos = ?
        GROUP BY location, modality
    """, (y_str,))
    y_sched = defaultdict(float)
    for r in cursor.fetchall():
        loc, mod, vol = r[0], (r[1] or "").strip(), float(r[2])
        norm = mod.upper().replace(" ","").replace("-","")
        w = WEIGHTS.get(norm, DEFAULT_WEIGHT)
        y_sched[loc] += vol * w
    total_y_sched = round(sum(y_sched.values()), 2)

    # Accuracy list
    acc_list = []
    for loc in cap_loc:
        s = round(y_sched[loc], 2)
        a = actual_dict.get(loc, 0.0)
        diff = round(a - s, 2)
        pct = round(a/s*100, 1) if s > 0 else 0
        acc_list.append((loc, s, a, diff, f"{pct}%" if s>0 else "N/A"))

    # ==================== BUILD REPORT ====================
    out = io.StringIO()

    print("="*80, file=out)
    print("EXECUTIVE SUMMARY - RADIOLOGY CAPACITY REPORT", file=out)
    print("="*80, file=out)
    print(f"Report Date: {date.today()}", file=out)
    print(f"Scheduled For: {start_date} to {end_date}", file=out)
    print(f"Total Active Sites: {len(loc_output)}", file=out)
    print(file=out)

    print(f"Network Scheduled Weighted: {total_scheduled:.2f}", file=out)
    print(f"Network Capacity (90th):   {total_capacity:.2f}", file=out)
    print(f"Network Utilization:       {round(total_scheduled/total_capacity*100,1)}%", file=out)
    print(file=out)

    over = sum(1 for r in loc_output if r[7]=="OVER CAPACITY")
    at   = sum(1 for r in loc_output if "AT CAPACITY" in r[7])
    under = len(loc_output) - over - at
    print(f"Sites OVER capacity:  {over}", file=out)
    print(f"Sites AT capacity:    {at}", file=out)
    print(f"Sites UNDER capacity: {under}", file=out)
    print(file=out)

    print("Top 5 Highest Utilization Sites:", file=out)
    for r in loc_sorted[:5]:
        pct = f"{r[5]:.1%}" if r[5] else "N/A"
        print(f"  • {r[1]:<15} {r[3]:>8.1f} weighted ({pct} of capacity) → {r[7]}", file=out)
    print("\n"+"="*80+"\n", file=out)

    # Yesterday section
    print("="*80, file=out)
    print(f"YESTERDAY'S PERFORMANCE - Actual vs Scheduled ({y_str})", file=out)
    print("="*80, file=out)
    print(format_table(sorted(acc_list, key=lambda x: float(x[4][:-1]) if x[4]!="N/A" else 0, reverse=True),
                      ["Location","Scheduled","Actual","Diff","% Accuracy"]), file=out)
    print(f"\nNetwork Yesterday: Scheduled {total_y_sched:.2f} | Actual {total_actual:.2f} | Accuracy {round(total_actual/total_y_sched*100,1) if total_y_sched>0 else 0}%", file=out)
    print("\n"+"="*80+"\n", file=out)

    # Original tables
    print(f"SCHEDULED WEIGHTED VOLUME — {start_date} → {end_date}", file=out)
    print("(Latest snapshot from v_Scheduled_Current; active locations only)\n", file=out)
    print("== Location Rollup ==\n", file=out)
    print(format_table(loc_sorted, ["dos","location","exams","weighted_units","capacity_90th","pct_of_capacity","gap_units","status"], max_rows=200), file=out)

    print("\n== Modality Detail ==\n", file=out)
    print(format_table(mod_output, ["dos","location","modality","exams","weighted_units","cap_mod","pct_of_capacity","status"], max_rows=400), file=out)

    if unknown:
        print("\nWARNING: Unknown modalities:", file=out)
        for m in sorted(unknown): print(" -", repr(m), file=out)

    report = out.getvalue()
    print(report)
    if args.send_email:
        send_report_email(report, recipients)

    conn.close()

if __name__ == "__main__":
    main()