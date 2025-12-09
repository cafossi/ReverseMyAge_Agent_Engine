"""Report export utilities for PDF and HTML generation (Touch Points / APEX_TP)."""

import os
import json
import markdown
from datetime import datetime
from typing import Optional, Dict, Any
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration


# =============================
# 🎨 Styling
# =============================
def get_report_css() -> str:
    """Get CSS styling for professional report appearance."""
    return """
    @page {
        size: A4;
        margin: 2cm;
        @top-center {
            content: "Excellence Performance Center - Confidential";
            font-size: 9pt;
            color: #666;
        }
        @bottom-right {
            content: "Page " counter(page) " of " counter(pages);
            font-size: 9pt;
            color: #666;
        }
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
        background: white;
    }

    h1 {
        color: #1a1a1a;
        border-bottom: 3px solid #0066cc;
        padding-bottom: 10px;
        margin-top: 0;
        font-size: 28px;
        text-align: center;
    }

    h2 {
        color: #0066cc;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 8px;
        margin-top: 30px;
        font-size: 22px;
    }

    h3 {
        color: #0066cc;
        margin-top: 25px;
        font-size: 18px;
    }

    h4 {
        color: #333;
        margin-top: 20px;
        font-size: 16px;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        font-size: 11px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    th {
        background-color: #0066cc;
        color: white;
        padding: 10px;
        text-align: left;
        font-weight: 600;
        border: 1px solid #0052a3;
    }

    td {
        padding: 8px 10px;
        border: 1px solid #e0e0e0;
    }

    tr:nth-child(even) {
        background-color: #f8f9fa;
    }

    tr:hover {
        background-color: #e3f2fd;
    }

    strong {
        color: #1a1a1a;
        font-weight: 600;
    }

    em {
        color: #0066cc;
        font-style: italic;
    }

    ul, ol {
        margin: 15px 0;
        padding-left: 30px;
    }

    li {
        margin: 8px 0;
        line-height: 1.6;
    }

    hr {
        border: none;
        border-top: 2px solid #e0e0e0;
        margin: 30px 0;
    }

    code {
        background-color: #f5f5f5;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
        font-size: 90%;
    }

    pre {
        background-color: #f5f5f5;
        padding: 15px;
        border-radius: 5px;
        overflow-x: auto;
        border-left: 4px solid #0066cc;
    }

    .page-break {
        page-break-after: always;
    }

    .report-footer {
        margin-top: 50px;
        padding-top: 20px;
        border-top: 2px solid #e0e0e0;
        text-align: center;
        font-size: 11px;
        color: #666;
    }

    @media print {
        body {
            margin: 0;
            padding: 10mm;
        }
        table, tr {
            page-break-inside: avoid;
        }
        h2, h3 {
            page-break-after: avoid;
        }
    }
    """


# =============================
# 🧩 Helpers
# =============================
def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _title_from_md(md: str, default: str = "EPC Report") -> str:
    for line in md.splitlines():
        if line.startswith("# "):
            return line.replace("# ", "").strip()
    return default


def _filters_to_md(filters: Dict[str, Any]) -> str:
    """Nicely render filter key/values as Markdown; omit Nones/empties."""
    clean = {k: v for k, v in filters.items() if v not in (None, "", [])}
    if not clean:
        return ""
    lines = ["\n---\n**Filters Applied**", ""]
    for k, v in clean.items():
        label = k.replace("_", " ").title()
        lines.append(f"- **{label}**: {v}")
    return "\n".join(lines)


# =============================
# 🧱 Conversions
# =============================
def markdown_to_html(markdown_content: str, title: str = "EPC Report") -> str:
    """Convert markdown report to styled HTML."""
    html_body = markdown.markdown(
        markdown_content,
        extensions=["tables", "fenced_code", "codehilite", "nl2br", "sane_lists"],
    )

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_document = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {get_report_css()}
    </style>
</head>
<body>
    {html_body}

    <div class="report-footer">
        <p><strong>Excellence Performance Center</strong></p>
        <p>Report generated on {timestamp}</p>
        <p>⚠️ Confidential - For Internal Use Only</p>
    </div>
</body>
</html>
"""
    return html_document


def html_to_pdf(html_content: str, output_path: str) -> str:
    """Convert HTML to PDF using WeasyPrint."""
    try:
        font_config = FontConfiguration()
        css = CSS(string=get_report_css(), font_config=font_config)
        HTML(string=html_content).write_pdf(
            output_path, stylesheets=[css], font_config=font_config
        )
        return output_path
    except Exception as e:
        raise Exception(f"PDF generation failed: {str(e)}")


def export_report(
    markdown_content: str,
    format: str = "html",
    output_dir: str = "./reports",
    filename: Optional[str] = None,
    html_override: Optional[str] = None,
) -> str:
    """
    Export report to HTML or PDF format.

    Args:
        markdown_content: Markdown report content (ignored if html_override is provided)
        format: 'html' or 'pdf'
        output_dir: Directory to save the report
        filename: Optional custom filename (without extension)
        html_override: If provided, use this HTML directly (e.g., DS-produced HTML)

    Returns:
        Path to the generated file
    """
    os.makedirs(output_dir, exist_ok=True)

    if not filename:
        filename = f"epc_report_{_now_stamp()}"

    # Prefer DS/agent-provided HTML if available
    if html_override:
        html_content = html_override
    else:
        title = _title_from_md(markdown_content, default="EPC Report")
        html_content = markdown_to_html(markdown_content, title)

    if format.lower() == "html":
        output_path = os.path.join(output_dir, f"{filename}.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return output_path

    if format.lower() == "pdf":
        output_path = os.path.join(output_dir, f"{filename}.pdf")
        html_to_pdf(html_content, output_path)
        return output_path

    raise ValueError(f"Unsupported format: {format}. Use 'html' or 'pdf'.")


# =============================
# 🚀 Standard Reports (TP)
# =============================
def export_standard_report(
    report_id: str,
    format: str = "html",
    output_dir: str = "./reports",
    html: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Generate and export a standard Touch Points report.

    Args:
        report_id: one of:
            - 'tp_site_analysis'
            - 'tp_region_analysis'
            - 'tp_customer_analysis'
            - 'tp_company_overview'
            - 'tp_exec_report'   (narrative)
            - (custom ids supported too)
        format: 'html' or 'pdf'
        output_dir: destination folder
        html: optional HTML payload (e.g., from DS agent) to render verbatim
        **kwargs: scope/filters
            Common:
              - customer_code: int
              - customer_name: str
              - location_number: str
              - region: str
              - start_date: 'YYYY-MM-DD'
              - end_date: 'YYYY-MM-DD'
            TP facets (optional):
              - tp_type, channel, priority, owner, status, etc.

    Returns:
        Path to the generated file.
    """
    # 1) If DS gave us HTML, we can export without markdown generation.
    if html:
        filename = _filename_for(report_id, **kwargs)
        return export_report(
            markdown_content="",  # ignored
            format=format,
            output_dir=output_dir,
            filename=filename,
            html_override=html,
        )

    # 2) Otherwise, build markdown using your Jinja/SQL generator
    #    (keeps your existing architecture intact).
    from .standard_reports import generate_standard_report

    markdown_content = generate_standard_report(report_id=report_id, **kwargs)

    # 3) Append a compact "Filters Applied" section for traceability (safe for exec PDFs)
    filters_md = _filters_to_md(kwargs)
    if filters_md:
        markdown_content = f"{markdown_content}\n{filters_md}\n"

    filename = _filename_for(report_id, **kwargs)
    return export_report(markdown_content, format, output_dir, filename)


def _filename_for(report_id: str, **kwargs) -> str:
    """Create descriptive filenames per TP report type."""
    ts = _now_stamp()

    # Normalize the most common kwargs we expect
    cc = kwargs.get("customer_code")
    cn = kwargs.get("customer_name")
    loc = kwargs.get("location_number") or kwargs.get("location_id")  # tolerate old param
    reg = kwargs.get("region")
    start = kwargs.get("start_date")
    end = kwargs.get("end_date")

    # Prefer canonical TP report ids
    if report_id == "tp_site_analysis":
        who = f"{cc or cn}_{loc}" if (cc or cn) and loc else (cc or cn or "site")
        return f"tp_site_analysis_{who}_{start or 'na'}_{end or 'na'}_{ts}"

    if report_id == "tp_customer_analysis":
        who = f"{cc or cn or 'customer'}"
        return f"tp_customer_analysis_{who}_{start or 'na'}_{end or 'na'}_{ts}"

    if report_id == "tp_region_analysis":
        who = reg or "region"
        return f"tp_region_analysis_{who}_{start or 'na'}_{end or 'na'}_{ts}"

    if report_id == "tp_company_overview":
        return f"tp_company_overview_{start or 'na'}_{end or 'na'}_{ts}"

    if report_id == "tp_exec_report":
        who = cn or cc or reg or "exec"
        return f"tp_exec_report_{who}_{start or 'na'}_{end or 'na'}_{ts}"

    # Backward compatibility with your older NBOT-like ids (optional)
    if report_id in ("site_health", "customer_overview", "region_overview"):
        # 🔁 Map to TP-style names but keep old pattern if you still call them
        map_name = {
            "site_health": f"tp_site_analysis_{cc or cn}_{loc or 'loc'}",
            "customer_overview": f"tp_customer_analysis_{cc or cn or 'customer'}",
            "region_overview": f"tp_region_analysis_{reg or 'region'}",
        }[report_id]
        return f"{map_name}_{start or 'na'}_{end or 'na'}_{ts}"

    # Default
    return f"{report_id}_{ts}"
