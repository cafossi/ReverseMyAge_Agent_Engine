"""Report export utilities for PDF and HTML generation."""

import os
import re
import markdown
from datetime import datetime
from typing import Optional, Tuple
from zoneinfo import ZoneInfo
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

# =============================
# 🎨 Styling
# =============================



def get_report_css() -> str:
    """Bold 3D Metallic design with extreme depth, chrome borders, and gap-free pagination."""
    return """
    /* ============================================
       PAGE SETUP - Controls PDF page size and margins
       ============================================ */
    @page {
        size: A4;
        margin: 1.2cm 1.5cm;
        
        /* Header text at top of every page */
        @top-center {
            content: "EXCELLENCE PERFORMANCE CENTER  |  CONFIDENTIAL";
            font-size: 7pt;
            color: #6b7280;
            font-weight: 700;
            letter-spacing: 1px;
        }
        
        /* Page numbers at bottom right */
        @bottom-right {
            content: counter(page) " / " counter(pages);
            font-size: 8pt;
            color: #1f2937;
            font-weight: 600;
        }
    }

    /* ============================================
       COLOR VARIABLES - Central color management
       ============================================ */
    :root {
        --text: #111827;
        --text-light: #4b5563;
        --muted: #6b7280;
        --primary-dark: #050911;
        --primary: #1e3a8a;
        --accent: #3b82f6;
        --border: #d1d5db;
        --bg-dark: #1f2937;
        --bg-light: #f3f4f6;
        --bg-accent: #dbeafe;
        --silver: #c0c0c0;
        --silver-dark: #606060;
        --silver-light: #f5f5f5;
        --chrome: #e8e8e8;
        --success: #059669;
        --warning: #d97706;
        --danger: #dc2626;
    }

    /* ============================================
       BODY - Main document background and font
       ============================================ */
    body {
        font-family: 'Roboto', 'Arial', sans-serif;
        line-height: 1.5;
        color: var(--text);
        max-width: 1200px;
        margin: 0 auto;
        padding: 0;
        /* UPDATED: Lighter background gradient */
        background: linear-gradient(135deg, #e5e7eb 0%, #d1d5db 100%);
        font-size: 10pt;
        font-weight: 400;
        orphans: 2;
        widows: 2;
    }

    /* ============================================
       H1 HEADER - Main report title (EXCELLENCE PERFORMANCE CENTER)
       Controls: Size, colors, 3D effects, borders
       ============================================ */
    h1 {
        color: white;
        background: 
            linear-gradient(135deg, 
                rgba(255,255,255,0.1) 0%, 
                transparent 20%, 
                transparent 80%, 
                rgba(0,0,0,0.2) 100%),
            linear-gradient(135deg, 
                #000814 0%, 
                #1e3a8a 25%, 
                #3b82f6 50%, 
                #1e3a8a 75%, 
                #000814 100%);
        padding: 24px 36px;
        margin: 0 0 20px 0;
        font-size: 16pt;
        font-weight: 800;
        text-align: center;
        letter-spacing: 0px;
        text-transform: uppercase;
        position: relative;
        
        /* 3D shadow depth effect */
        box-shadow: 
            0 2px 0 #505050,
            0 4px 0 #707070,
            0 6px 0 #909090,
            0 8px 0 #b0b0b0,
            0 10px 0 #d0d0d0,
            0 15px 30px rgba(0,0,0,0.5),
            inset 0 -4px 8px rgba(0,0,0,0.4),
            inset 0 4px 8px rgba(255,255,255,0.2);
        
        /* Chrome metallic border */
        border: 9px solid;
        border-image: linear-gradient(135deg, 
            #ffffff 0%, 
            #c0c0c0 25%, 
            #606060 50%, 
            #c0c0c0 75%, 
            #ffffff 100%) 1;
        
        /* Text shadow for 3D effect */
        text-shadow: 
            2px 2px 0 rgba(0,0,0,0.4),
            4px 4px 0 rgba(0,0,0,0.3),
            6px 6px 0 rgba(0,0,0,0.2),
            8px 8px 15px rgba(0,0,0,0.6),
            0 0 40px rgba(59,130,246,0.5);
        
        /* Prevent page breaks after H1 */
        break-after: avoid-page;
        page-break-after: avoid;
    }

    /* Chrome reflection effect on H1 */
    h1::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 60%;
        background: linear-gradient(180deg, 
            rgba(255,255,255,0.25) 0%,
            rgba(255,255,255,0.1) 30%, 
            transparent 100%);
        pointer-events: none;
    }

    /* Bottom shadow highlight on H1 */
    h1::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 8px;
        background: linear-gradient(180deg, 
            transparent 0%, 
            rgba(0,0,0,0.4) 100%);
        pointer-events: none;
    }

    /* ============================================
       CONTENT WRAPPER - White content area
       ============================================ */
    .content {
        padding: 0 24px;
        background: white;
    }

    /* ============================================
       H2 HEADERS - Section headers (EXECUTIVE SUMMARY, KEY METRICS, etc.)
       Controls: Size, colors, 3D effects, chrome borders
       ============================================ */
    h2 {
        color: white;
        background: 
            linear-gradient(135deg, 
                rgba(255,255,255,0.08) 0%, 
                transparent 20%, 
                transparent 80%, 
                rgba(0,0,0,0.15) 100%),
            linear-gradient(135deg, 
                #000000 0%, 
                #1f2937 30%, 
                #374151 50%, 
                #1f2937 70%, 
                #000000 100%);
        padding: 12px 24px;
        margin: 32px -24px 24px -24px;
        font-size: 15pt;
        font-weight: 900;
        letter-spacing: 1px;
        text-transform: uppercase;
        position: relative;
        
        /* 3D shadow depth */
        box-shadow: 
            0 2px 0 #808080,
            0 4px 0 #a0a0a0,
            0 6px 0 #c0c0c0,
            0 8px 16px rgba(0,0,0,0.4),
            inset 0 -3px 6px rgba(0,0,0,0.5),
            inset 0 3px 6px rgba(255,255,255,0.25);
        
        /* Chrome accent border on left */
        border: 5px solid;
        border-image: linear-gradient(90deg, 
            #3b82f6 0%, 
            #ffffff 5%, 
            #808080 10%, 
            #ffffff 15%, 
            transparent 15%, 
            transparent 100%) 1;
        border-left-width: 8px;
        border-bottom: 4px solid var(--silver-dark);
        border-top: 2px solid rgba(255,255,255,0.3);
        
        /* Text shadow for depth */
        text-shadow: 
            2px 2px 0 rgba(0,0,0,0.4),
            3px 3px 0 rgba(0,0,0,0.3),
            4px 4px 8px rgba(0,0,0,0.6);
        
        /* Prevent page breaks after H2 */
        break-after: avoid-page;
        page-break-after: avoid;
        orphans: 2;
        widows: 2;
    }

    /* Chrome reflection on H2 */
    h2::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 50%;
        background: linear-gradient(180deg, 
            rgba(255,255,255,0.15) 0%, 
            transparent 100%);
        pointer-events: none;
    }

    /* ============================================
       H3 HEADERS - Subsection headers (KEY FINDINGS, NBOT COMPOSITION, etc.)
       Controls: Size, colors, metallic effects
       ============================================ */
    h3 {
        color: #000000;
        margin-top: 28px;
        margin-bottom: 14px;
        font-size: 12pt;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 1px;
        padding: 12px 20px;
        background: 
            linear-gradient(135deg, 
                rgba(255,255,255,0.5) 0%, 
                transparent 20%, 
                transparent 80%, 
                rgba(0,0,0,0.1) 100%),
            linear-gradient(135deg, 
                #f8fafc 0%, 
                #cbd5e1 50%, 
                #f8fafc 100%);
        border: 4px solid;
        border-image: linear-gradient(90deg, 
            #3b82f6 0%, 
            #ffffff 3%, 
            #808080 6%, 
            #ffffff 9%, 
            transparent 9%) 1;
        border-left-width: 6px;
        box-shadow: 
            0 3px 6px rgba(0,0,0,0.2),
            inset 0 2px 4px rgba(255,255,255,0.6),
            inset 0 -1px 3px rgba(0,0,0,0.2);
        text-shadow: 
            1px 1px 0 rgba(255,255,255,0.8),
            2px 2px 4px rgba(255,255,255,0.5);
        
        break-after: avoid-page;
        page-break-after: avoid;
    }

    /* ============================================
       H4 HEADERS - Minor subsections
       ============================================ */
    h4 {
        color: var(--text);
        margin-top: 16px;
        margin-bottom: 8px;
        font-size: 10pt;
        font-weight: 700;
        break-after: avoid-page;
        page-break-after: avoid;
    }

    /* ============================================
       TABLES - All data tables
       Controls: Borders, spacing, page break behavior
       ============================================ */
    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 9pt;  /* Base table font size */
        margin: 20px 0 28px 0;
        box-shadow: 
            0 3px 0 var(--silver-dark),
            0 6px 12px rgba(0,0,0,0.25);
        border: 4px solid;
        border-image: linear-gradient(135deg, 
            var(--silver-light) 0%, 
            var(--silver-dark) 50%, 
            var(--silver-light) 100%) 1;
        
        /* CRITICAL: Allow tables to split across pages */
        break-inside: auto;
        page-break-inside: auto;
    }

    /* Repeat table headers on each page */
    thead { display: table-header-group; }
    tfoot { display: table-footer-group; }

    /* ============================================
       TABLE HEADERS (TH) - Column headers
       Controls: Background, colors, borders, alignment
       ============================================ */
    th {
        background: 
            linear-gradient(180deg, 
                rgba(255,255,255,0.05) 0%, 
                transparent 100%),
            linear-gradient(180deg, 
                #4b5563 0%, 
                #1f2937 50%, 
                #000000 100%);
        color: white;
        padding: 16px 14px;
        /* UPDATED: Center all table headers */
        text-align: center;
        font-weight: 900;
        /* UPDATED: Larger header font */
        font-size: 11pt;
        border-right: 2px solid #606060;
        text-transform: uppercase;
        letter-spacing: 1px;
        text-shadow: 
            1px 1px 0 rgba(0,0,0,0.5),
            2px 2px 4px rgba(0,0,0,0.7),
            0 0 15px rgba(59,130,246,0.4);
        border-bottom: 4px solid var(--silver);
        box-shadow: 
            inset 0 2px 4px rgba(255,255,255,0.15),
            inset 0 -1px 3px rgba(0,0,0,0.3);
    }

    th:last-child { border-right: none; }

    /* ============================================
       TABLE CELLS (TD) - Data cells
       Controls: Padding, borders, text size, alignment
       ============================================ */
    td {
        padding: 14px;
        border-bottom: 1px solid #cbd5e1;
        border-right: 1px solid #cbd5e1;
        /* UPDATED: Larger data cell font */
        font-size: 11pt;
        background: white;
        font-weight: 500;
        line-height: 1.5;
        
        /* Keep cells intact during page breaks */
        break-inside: avoid;
        page-break-inside: avoid;
    }

    td:last-child { border-right: none; }

    /* ============================================
       TABLE ROWS (TR) - Row behavior
       Keep rows together during page breaks
       ============================================ */
    tr {
        break-inside: avoid;
        page-break-inside: avoid;
    }

    /* Alternating row colors */
    tr:nth-child(even) td { 
        background: linear-gradient(180deg, #f9fafb 0%, #f3f4f6 100%); 
    }

    tr:hover td { background-color: var(--bg-accent); }

    /* Right-aligned numeric columns */
    td[style*="text-align: right"],
    td[style*="text-align:right"] {
        font-weight: 700;
        color: var(--text);
        max-width: 80px;
        white-space: nowrap;
    }

    /* ============================================
       TEXT FORMATTING
       ============================================ */
    strong {
        color: var(--text);
        font-weight: 900;
    }

    em {
        color: var(--primary);
        font-style: normal;
        font-weight: 700;
    }

    /* ============================================
       LISTS (UL/OL) - Bullet points and numbered lists
       Controls sections like "Key Findings", "Recommendations", etc.
       ============================================ */
    ul, ol {
        margin: 16px 0;
        padding-left: 32px;
    }

    /* UPDATED: Smaller bullet text under sections */
    li {
        margin: 12px 0;
        line-height: 1.7;
        font-size: 9.5pt;  /* Reduced from 10.5pt */
        color: var(--text);
        font-weight: 600;
    }

    li::marker {
        color: var(--primary);
        font-weight: 900;
    }

    /* ============================================
       HORIZONTAL RULES
       ============================================ */
    hr {
        border: none;
        border-top: 3px solid var(--border);
        margin: 24px 0;
        break-after: auto;
        page-break-after: auto;
    }

    /* ============================================
       PARAGRAPHS
       ============================================ */
    p {
        margin: 14px 0;
        line-height: 1.7;
        color: var(--text);
        font-weight: 400;
        break-after: auto;
        page-break-after: auto;
        orphans: 2;
        widows: 2;
    }

    /* ============================================
       CODE BLOCKS
       ============================================ */
    code {
        background-color: var(--bg-light);
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
        font-size: 9pt;
    }

    pre {
        background-color: var(--bg-light);
        padding: 12px;
        border-radius: 4px;
        overflow-x: auto;
        border-left: 3px solid var(--primary);
        font-size: 9pt;
        break-inside: avoid;
        page-break-inside: avoid;
    }

    /* ============================================
       PAGE BREAKS
       ============================================ */
    .page-break {
        page-break-after: always;
        break-after: page;
    }

    /* ============================================
       STATUS BADGES - Emoji replacements (RED, YEL, GRN, ORG, !)
       Controls: Size, colors, 3D effects
       ============================================ */
    .status-badge {
        display: inline-block;
        /* UPDATED: Smaller badge size */
        padding: 3px 10px;
        border-radius: 5px;
        /* UPDATED: Smaller badge font */
        font-size: 7.5pt;
        font-weight: 900;
        color: white;
        vertical-align: middle;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        position: relative;
        
        /* Dramatic badge depth */
        box-shadow: 
            0 2px 0 rgba(0,0,0,0.3),
            0 4px 0 rgba(0,0,0,0.2),
            0 6px 12px rgba(0,0,0,0.4),
            inset 0 -2px 4px rgba(0,0,0,0.4),
            inset 0 2px 4px rgba(255,255,255,0.4);
        border: 2px solid rgba(255,255,255,0.3);
        border-bottom: 3px solid rgba(0,0,0,0.3);
    }

    /* Badge color variants */
    .badge-red { 
        background: linear-gradient(135deg, #f87171 0%, #ef4444 50%, #dc2626 100%); 
    }
    .badge-orange { 
        background: linear-gradient(135deg, #fb923c 0%, #f97316 50%, #ea580c 100%); 
    }
    .badge-yellow { 
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 50%, #d97706 100%); 
    }
    .badge-green { 
        background: linear-gradient(135deg, #34d399 0%, #10b981 50%, #059669 100%); 
    }
    .badge-alert { 
        background: linear-gradient(135deg, #9ca3af 0%, #6b7280 50%, #4b5563 100%); 
    }

    /* ============================================
       FOOTER - Report generation info
       ============================================ */
    .report-footer {
        margin-top: 48px;
        padding: 20px 0;
        border-top: 4px solid;
        border-image: linear-gradient(90deg, 
            var(--silver-light) 0%, 
            var(--silver-dark) 50%, 
            var(--silver-light) 100%) 1;
        text-align: center;
        font-size: 8pt;
        color: var(--muted);
        font-weight: 700;
        break-inside: avoid;
        page-break-inside: avoid;
    }

    /* ============================================
       PDF PRINT MEDIA QUERY
       Controls final PDF output appearance
       ============================================ */
    @media print {
        body {
            margin: 0;
            padding: 0;
            font-size: 9.5pt;
            background: white;
        }

        /* Reduce header sizes for print */
        h1 {
            font-size: 26pt;
            padding: 24px 32px;
            margin: 0 0 16px 0;
            box-shadow: 
                0 2px 0 #606060,
                0 4px 0 #808080,
                0 6px 0 #a0a0a0,
                0 10px 20px rgba(0,0,0,0.4),
                inset 0 -3px 6px rgba(0,0,0,0.3),
                inset 0 3px 6px rgba(255,255,255,0.2);
        }

        h2 {
            font-size: 13pt;
            margin: 20px 0 14px 0;
            padding: 10px 18px;
            box-shadow: 
                0 2px 0 #909090,
                0 4px 0 #b0b0b0,
                0 6px 12px rgba(0,0,0,0.3),
                inset 0 -2px 4px rgba(0,0,0,0.4),
                inset 0 2px 4px rgba(255,255,255,0.2);
        }

        h3 {
            font-size: 10pt;
            margin-bottom: 10px;
        }

        h4 {
            font-size: 9pt;
        }

        .content {
            padding: 0 12mm;
        }

        /* ============================================
           TABLE PRINT ADJUSTMENTS
           ============================================ */
        table {
            font-size: 7.5pt;  /* Smaller for print */
            margin: 12px 0 20px 0;
            width: 100%;
            break-inside: auto;
            page-break-inside: auto;
        }

        thead { display: table-header-group; }
        tfoot { display: table-footer-group; }

        tr {
            break-inside: avoid;
            page-break-inside: avoid;
        }

        th {
            font-size: 8pt;
            padding: 12px 8px;
            /* Centered headers in print */
            text-align: center;
        }

        td {
            font-size: 8pt;
            padding: 10px 8px;
            max-width: 150px;
            line-height: 1.4;
        }

        /* Right-aligned numeric columns */
        td[style*="text-align: right"],
        td[style*="text-align:right"] {
            max-width: 70px;
            white-space: nowrap;
        }

        /* Remove hover effects in print */
        tr:hover td {
            background-color: inherit;
        }

        /* Smaller badges in print */
        .status-badge {
            font-size: 6.5pt;
            padding: 2px 8px;
        }

        /* Smaller list items in print */
        li {
            font-size: 8.5pt;
        }
    }
    """


# =============================
# 🧱 Conversions
# =============================

def convert_emojis_to_badges(html_content: str) -> str:
    """
    Convert emojis to styled badge elements for better PDF rendering.
    
    Args:
        html_content: HTML content with emojis
    
    Returns:
        HTML content with badges instead of emojis
    """
    # Replace emoji patterns with badge spans
    replacements = {
        '🔴': '<span class="status-badge badge-red">RED</span>',
        '🟠': '<span class="status-badge badge-orange">ORG</span>',  # ✅ FIXED
        '🟡': '<span class="status-badge badge-yellow">YEL</span>',
        '🟢': '<span class="status-badge badge-green">GRN</span>',
        '⚠️': '<span class="status-badge badge-alert">!</span>',
        '⚠': '<span class="status-badge badge-alert">!</span>',
        '☑️': '✓',
        '☑': '✓',
        # Remove other decorative emojis that don't render well
        '📋': '',
        '📊': '',
        '📅': '',
        '📈': '',
        '💡': '',
        '🧾': '',
        '🧩': '',
        '📍': '',
    }
    
    for emoji, replacement in replacements.items():
        html_content = html_content.replace(emoji, replacement)
    
    return html_content


def markdown_to_html(markdown_content: str, title: str = "EPC Report") -> str:
    """Convert markdown report to styled HTML."""
    
    # Convert markdown to HTML
    html_body = markdown.markdown(
        markdown_content,
        extensions=[
            'tables',
            'fenced_code',
            'codehilite',
            'nl2br',
            'sane_lists'
        ]
    )
    
    # Convert emojis to badges for better PDF rendering
    html_body = convert_emojis_to_badges(html_body)
    
    # Get current timestamp in CST
    timestamp = get_cst_timestamp("%Y-%m-%d %H:%M:%S")
    
    # Build complete HTML document
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
        # Create font configuration
        font_config = FontConfiguration()
        
        # Create CSS
        css = CSS(string=get_report_css(), font_config=font_config)
        
        # Generate PDF
        HTML(string=html_content).write_pdf(
            output_path,
            stylesheets=[css],
            font_config=font_config
        )
        
        return output_path
    except Exception as e:
        raise Exception(f"PDF generation failed: {str(e)}")


def export_report(
    markdown_content: str,
    format: str = 'html',
    output_dir: str = './reports',
    filename: Optional[str] = None
) -> str:
    """
    Export report to HTML or PDF format.
    
    Args:
        markdown_content: The markdown report content
        format: 'html' or 'pdf'
        output_dir: Directory to save the report
        filename: Optional custom filename (without extension)
    
    Returns:
        Path to the generated file
    """
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename if not provided
    if not filename:
        timestamp = get_cst_timestamp("%Y-%m-%d_%H-%M-%S")
        filename = f"epc_report_{timestamp}"
    
    # Extract title from markdown (first H1)
    title = "EPC Report"
    for line in markdown_content.split('\n'):
        if line.startswith('# '):
            title = line.replace('# ', '').strip()
            break
    
    # Convert markdown to HTML
    html_content = markdown_to_html(markdown_content, title)
    
    if format.lower() == 'html':
        # Save HTML
        output_path = os.path.join(output_dir, f"{filename}.html")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return output_path
    
    elif format.lower() == 'pdf':
        # Save PDF
        output_path = os.path.join(output_dir, f"{filename}.pdf")
        html_to_pdf(html_content, output_path)
        return output_path
    
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'html' or 'pdf'")


# =============================
# 🚀 HTML Report Export (NEW)
# =============================

def export_html_report(
    html_content: str,
    output_dir: str = './reports',
    filename: Optional[str] = None
) -> str:
    """
    Export pre-generated HTML content to a file.
    
    Args:
        html_content: Complete HTML document
        output_dir: Directory to save the report
        filename: Optional custom filename (without extension)
    
    Returns:
        Path to the generated HTML file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename if not provided
    if not filename:
        timestamp = get_cst_timestamp("%Y-%m-%d_%H-%M-%S")
        filename = f"epc_report_{timestamp}"
    
    # Build output path
    output_path = os.path.join(output_dir, f"{filename}.html")
    
    # Write HTML content to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_path


# =============================
# 🔧 Utility Functions
# =============================

def get_cst_timestamp(format_str: str = "%Y-%m-%d_%H-%M-%S") -> str:
    """
    Get current timestamp in CST timezone.
    
    Args:
        format_str: strftime format string
    
    Returns:
        Formatted timestamp string in CST
    """
    cst = ZoneInfo('America/Chicago')
    now_cst = datetime.now(cst)
    return now_cst.strftime(format_str)


def extract_report_metadata(markdown_content: str, report_id: str) -> dict:
    """
    Extract metadata from generated markdown content.
    
    Args:
        markdown_content: The markdown report content
        report_id: Type of report
    
    Returns:
        Dictionary with extracted metadata (customer_name, customer_code, location_number, region, etc.)
    """
    metadata = {}
    
    # Extract customer name and code from report title/header
    # Pattern: "Customer Name (CODE)" or "Customer Name – Location"
    customer_pattern = r'##\s+NBOT\s+\w+\s+Analysis\s+[–-]\s+([^(]+?)\s*\((\d+)\)'
    customer_match = re.search(customer_pattern, markdown_content)
    if customer_match:
        metadata['customer_name'] = customer_match.group(1).strip()
        metadata['customer_code'] = customer_match.group(2).strip()
    
    # Alternative pattern: Look for customer info in the content
    if not metadata.get('customer_name'):
        # Pattern: "**Customer Name – Location NUMBER**" (for site reports)
        site_pattern = r'\*\*([^–]+?)\s*–\s*Location\s+(\w+)\*\*'
        site_match = re.search(site_pattern, markdown_content)
        if site_match:
            metadata['customer_name'] = site_match.group(1).strip()
            metadata['site_id'] = site_match.group(2).strip()
    
    # Extract location/site number
    location_pattern = r'Location\s+(\w+)'
    location_match = re.search(location_pattern, markdown_content)
    if location_match:
        metadata['site_id'] = location_match.group(1).strip()
    
    # Extract region
    region_pattern = r'##\s+NBOT\s+Region\s+Analysis\s+[–-]\s+([^\n]+)'
    region_match = re.search(region_pattern, markdown_content)
    if region_match:
        metadata['region'] = region_match.group(1).strip()
    
    # Alternative region pattern
    if not metadata.get('region'):
        region_pattern2 = r'\*\*Region:\*\*\s+([^\n|]+)'
        region_match2 = re.search(region_pattern2, markdown_content)
        if region_match2:
            metadata['region'] = region_match2.group(1).strip()
    
    return metadata


def sanitize_filename_component(text: str) -> str:
    """
    Sanitize a text string for use in filenames.
    
    Args:
        text: Text to sanitize
    
    Returns:
        Sanitized text safe for filenames
    """
    if not text:
        return "unknown"
    
    # Convert to string and strip whitespace
    text = str(text).strip()
    
    # Replace spaces with underscores
    text = text.replace(' ', '_')
    
    # Remove any characters that aren't alphanumeric, underscore, or hyphen
    text = re.sub(r'[^\w\-]', '', text)
    
    # Collapse multiple underscores
    text = re.sub(r'_+', '_', text)
    
    # Remove leading/trailing underscores
    text = text.strip('_')
    
    # If empty after sanitization, return default
    return text if text else "unknown"


def build_filename(report_id: str, timestamp: str, **kwargs) -> str:
    """
    Build a descriptive filename for a report.
    
    Args:
        report_id: Type of report
        timestamp: Formatted timestamp string
        **kwargs: Report parameters
    
    Returns:
        Formatted filename (without extension)
    """
    # Extract and sanitize components
    customer_name = sanitize_filename_component(kwargs.get('customer_name'))
    customer_code = sanitize_filename_component(kwargs.get('customer_code'))
    site_id = sanitize_filename_component(kwargs.get('site_id') or kwargs.get('location_id'))
    region = sanitize_filename_component(kwargs.get('region'))
    
    # Sanitize report_id
    report_type = sanitize_filename_component(report_id)
    
    # Build filename components list
    parts = [report_type]
    
    # Check if we have customer information
    has_customer_info = (customer_name != "unknown" or customer_code != "unknown")
    
    # Check if it's a site-specific report
    is_site_specific = (site_id and site_id != "unknown")
    
    # Special handling for specific report types
    if report_id in ['region_overview', 'nbot_region_analysis', 'nbot_region_analysis_by_site']:
        # Region reports don't need customer info
        # Format: {report_type}_{region}_{timestamp}
        parts = [report_type, region, timestamp]
    
    elif report_id in ['nbot_customer_analysis', 'customer_overview']:
        # Customer analysis should NEVER include site info, even if present
        # Format: {report_type}_{customer_name}_{customer_code}_{timestamp}
        if has_customer_info:
            parts = [report_type, customer_name, customer_code, timestamp]
        else:
            parts = [report_type, timestamp]
    
    elif report_id in ['nbot_site_analysis', 'site_health'] or is_site_specific:
        # Site-specific reports
        # Format: {report_type}_{customer_name}_{customer_code}_site_{site_id}_{timestamp}
        if has_customer_info:
            parts = [report_type, customer_name, customer_code, 'site', site_id, timestamp]
        else:
            parts = [report_type, 'site', site_id, timestamp]
    
    elif has_customer_info:
        # Customer-level reports (fallback)
        # Format: {report_type}_{customer_name}_{customer_code}_{timestamp}
        parts = [report_type, customer_name, customer_code, timestamp]
    
    else:
        # Generic fallback when no specific info available
        # Format: {report_type}_{timestamp}
        parts = [report_type, timestamp]
    
    # Join all parts with underscores
    filename = '_'.join(parts)
    
    return filename


# =============================
# 🚀 Standard Reports 
# =============================

def export_standard_report(
    report_id: str,
    format: str = 'html',
    output_dir: str = './reports',
    **kwargs
) -> str:
    """
    Generate and export a standard report.
    
    Args:
        report_id: Type of report ('site_health', 'customer_overview', 'region_overview', etc.)
        format: 'html' or 'pdf'
        output_dir: Directory to save the report
        **kwargs: Parameters for the report (customer_name, customer_code, site_id, location_id, region, dates, etc.)
    
    Returns:
        Path to the generated file
    
    Example filenames:
        - nbot_site_analysis_Acme_Corp_ACME001_site_NYC001_2024-10-07_14-30-22.pdf
        - nbot_customer_analysis_Acme_Corp_ACME001_2024-10-07_14-30-22.html
        - nbot_region_analysis_Northeast_2024-10-07_14-30-22.pdf
        - 4Week_NBOT_Snapshot_Customer_Waymo_LLC_Oct12-Nov08_2025.html
    """
    
    from .standard_reports import generate_standard_report
    
    # Generate the report content (only once)
    result = generate_standard_report(report_id=report_id, **kwargs)
    
    # Check if result is a tuple (HTML content + custom filename)
    # This happens with 4-week snapshot reports that generate their own filenames
    if isinstance(result, tuple):
        content, custom_filename = result
        # Remove .html extension if present (we'll add it back based on format)
        filename_base = custom_filename.replace('.html', '').replace('.pdf', '')
    else:
        # Single return value (markdown or HTML content)
        content = result
        custom_filename = None
        filename_base = None
    
    # Create readable timestamp in CST (for fallback)
    timestamp = get_cst_timestamp("%Y-%m-%d_%H-%M-%S")
    
    # Check if content is already HTML (for snapshot reports)
    if content.strip().startswith('<!DOCTYPE html>'):
        # Handle HTML-native reports (like 4-week snapshot)
        
        # Use custom filename if provided, otherwise generate generic one
        if filename_base:
            filename = filename_base
        else:
            filename = f"{report_id}_{timestamp}"
        
        if format.lower() == 'html':
            # Save HTML directly
            return export_html_report(content, output_dir, filename)
        elif format.lower() == 'pdf':
            # Convert HTML to PDF
            output_path = os.path.join(output_dir, f"{filename}.pdf")
            html_to_pdf(content, output_path)
            return output_path
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'html' or 'pdf'")
    
    else:
        # Handle Markdown reports (existing reports)
        # Extract metadata from the generated markdown to get actual customer/site info
        extracted_metadata = extract_report_metadata(content, report_id)
        
        # Merge extracted metadata with original kwargs (extracted takes precedence)
        merged_params = {**kwargs, **extracted_metadata}
        
        # Build descriptive filename
        filename = build_filename(report_id, timestamp, **merged_params)
        
        # Export using the existing markdown pipeline
        return export_report(content, format, output_dir, filename)