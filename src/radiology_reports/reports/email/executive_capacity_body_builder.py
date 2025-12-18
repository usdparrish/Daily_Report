def build_executive_capacity_email_content(report_text: str) -> tuple[str, str]:
    """
    Builds the subject and HTML body for the executive capacity report email.
    Parses metrics from the report text and applies formatting.
    Pure function: no I/O or side effects.

    :param report_text: The plain-text report content to parse and format.
    :return: Tuple of (subject, html_body).
    """
    lines = report_text.splitlines()
    utilization = "N/A"
    over_count = "?"
    dos = "Unknown"
    try:
        util_line = next((l for l in lines if "Network Utilization" in l), None)
        over_line = next((l for l in lines if "Sites OVER capacity" in l), None)
        dos_line = next((l for l in lines if "Scheduled For:" in l), None)
        
        if util_line:
            utilization = util_line.split(":")[1].strip()
        if over_line:
            over_count = over_line.split(":")[1].strip().split()[0]
        if dos_line:
            dos = dos_line.split("Scheduled For:")[1].strip().split(" to ")[0]
    except Exception:
        pass

    subject = f"Capacity Alert – {over_count} Sites Over ({utilization})"

    colored_report = (
        report_text
        .replace("OVER CAPACITY", '<span style="color: #e74c3c; font-weight: bold;">OVER CAPACITY</span>')
        .replace("AT CAPACITY", '<span style="color: #27ae60; font-weight: bold;">AT CAPACITY</span>')
        .replace("UNDER CAPACITY (GAP)", '<span style="color: #3498db; font-weight: bold;">UNDER CAPACITY (GAP)</span>')
        .replace("UNDER (GAP)", '<span style="color: #3498db; font-weight: bold;">UNDER (GAP)</span>')
    )

    html = f"""
    <html>
    <body style="font-family: Calibri, Arial, sans-serif; line-height: 1.6; color: #333;">
      <h2 style="color: #2c3e50;">Daily Radiology Capacity Report</h2>
      <p><strong>Tomorrow ({dos}) forecast:</strong></p>
      
      <div style="background: #f8f9fa; padding: 15px; border-left: 6px solid #3498db; margin: 20px 0;">
        <p><strong>Network Utilization:</strong> <span style="font-size: 1.2em;">{utilization}</span></p>
        <p><strong>Status:</strong>
          <span style="color: #e74c3c;"><strong>{over_count} sites OVER CAPACITY</strong></span> •
          <span style="color: #27ae60;">AT CAPACITY</span> •
          <span style="color: #3498db;">UNDER</span>
        </p>
      </div>

      <p><strong>Top 5 Hot Spots – Action Required</strong></p>
      <table style="width: 100%; max-width: 650px; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #2c3e50; color: white;">
          <th align="left" style="padding: 10px;">Site</th>
          <th align="right" style="padding: 10px;">Utilization</th>
          <th align="right" style="padding: 10px;">Weighted</th>
          <th align="center" style="padding: 10px;">Status</th>
        </tr>
    """

    top5_started = False
    for line in lines:
        if "Top 5 Highest Utilization Sites:" in line:
            top5_started = True
            continue
        if top5_started and line.strip().startswith(" • "):
            parts = line.strip()[3:].split()
            site = parts[0]
            weighted = parts[1]
            pct = parts[3].replace("(", "").replace(")", "")
            status = " ".join(parts[5:])
            color = "#e74c3c" if "OVER" in status else "#27ae60" if "AT" in status else "#3498db"
            html += f"""
            <tr style="background: {'#fdf2f2' if 'OVER' in status else '#f2fdf2'};">
              <td style="padding: 10px;"><strong>{site}</strong></td>
              <td align="right" style="padding: 10px; color: {color};"><strong>{pct}</strong></td>
              <td align="right" style="padding: 10px;">{weighted}</td>
              <td align="center" style="padding: 10px; color: {color};"><strong>{status}</strong></td>
            </tr>
            """
        elif top5_started and not line.strip().startswith(" • ") and line.strip():
            break

    html += f"""
      </table>

      <p style="color: #7f8c8d; font-size: 90%;">
        <em>Full location and modality tables below for reference.</em>
      </p>

      <pre style="background: #f5f5f5; padding: 15px; border: 1px solid #eee; font-size: 10pt; font-family: Consolas; line-height: 1.3;">
{colored_report}
      </pre>

      <hr style="border: 0; border-top: 1px solid #eee; margin: 40px 0;">
      <p style="color: #95a5a6; font-size: 85%;">Automated • Radiology Operations</p>
    </body>
    </html>
    """

    return subject, html