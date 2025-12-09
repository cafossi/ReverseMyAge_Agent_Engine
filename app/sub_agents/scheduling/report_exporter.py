"""Report export utilities for PDF and HTML generation."""

import os
import re
import markdown
from datetime import datetime
from typing import Optional, Tuple, List, Set

from .schedule_reports.common.filename_utils import generate_pareto_optimization_filename

# Try multiple methods to get CST timezone
try:
    from zoneinfo import ZoneInfo
    HAS_ZONEINFO = True
except ImportError:
    HAS_ZONEINFO = False
    try:
        import pytz
        HAS_PYTZ = True
    except ImportError:
        HAS_PYTZ = False

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
        max-width: 1380px;
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
        font-size: 22pt;
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
       H2 HEADERS - Section headers
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
       H3 HEADERS - Subsection headers
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
       TABLE HEADERS (TH)
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
        text-align: center;
        font-weight: 900;
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
       TABLE CELLS (TD)
       ============================================ */
    td {
        padding: 14px;
        border-bottom: 1px solid #cbd5e1;
        border-right: 1px solid #cbd5e1;
        font-size: 11pt;
        background: white;
        font-weight: 500;
        line-height: 1.5;
        break-inside: avoid;
        page-break-inside: avoid;
    }
    td:last-child { border-right: none; }

    /* ============================================
       TABLE ROWS (TR)
       ============================================ */
    tr {
        break-inside: avoid;
        page-break-inside: avoid;
    }
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
    strong { color: var(--text); font-weight: 900; }
    em { color: var(--primary); font-style: normal; font-weight: 700; }

    /* ============================================
       LISTS (UL/OL)
       ============================================ */
    ul, ol { margin: 16px 0; padding-left: 32px; }
    li {
        margin: 12px 0;
        line-height: 1.7;
        font-size: 9.5pt;
        color: var(--text);
        font-weight: 600;
    }
    li::marker { color: var(--primary); font-weight: 900; }

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
    .page-break { page-break-after: always; break-after: page; }

    /* ============================================
       STATUS BADGES
       ============================================ */
    .status-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 5px;
        font-size: 7.5pt;
        font-weight: 900;
        color: white;
        vertical-align: middle;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        position: relative;
        box-shadow: 
            0 2px 0 rgba(0,0,0,0.3),
            0 4px 0 rgba(0,0,0,0.2),
            0 6px 12px rgba(0,0,0,0.4),
            inset 0 -2px 4px rgba(0,0,0,0.4),
            inset 0 2px 4px rgba(255,255,255,0.4);
        border: 2px solid rgba(255,255,255,0.3);
        border-bottom: 3px solid rgba(0,0,0,0.3);
    }
    .badge-red { background: linear-gradient(135deg, #f87171 0%, #ef4444 50%, #dc2626 100%); }
    .badge-orange { background: linear-gradient(135deg, #fb923c 0%, #f97316 50%, #ea580c 100%); }
    .badge-yellow { background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 50%, #d97706 100%); }
    .badge-green { background: linear-gradient(135deg, #34d399 0%, #10b981 50%, #059669 100%); }
    .badge-alert { background: linear-gradient(135deg, #9ca3af 0%, #6b7280 50%, #4b5563 100%); }

    /* ============================================
       FOOTER
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
       ============================================ */
    @media print {
        body {
            margin: 0;
            padding: 0;
            font-size: 9.5pt;
            background: white;
        }
        h1 {
            font-size: 20pt;
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
        h3 { font-size: 10pt; margin-bottom: 10px; }
        h4 { font-size: 9pt; }
        .content { padding: 0 12mm; }

        table {
            font-size: 7.5pt;
            margin: 12px 0 20px 0;
            width: 100%;
            break-inside: auto;
            page-break-inside: auto;
        }
        thead { display: table-header-group; }
        tfoot { display: table-footer-group; }
        tr { break-inside: avoid; page-break-inside: avoid; }
        th { font-size: 8pt; padding: 12px 8px; text-align: center; }
        td { font-size: 8pt; padding: 10px 8px; max-width: 150px; line-height: 1.4; }
        td[style*="text-align: right"],
        td[style*="text-align:right"] {
            max-width: 70px;
            white-space: nowrap;
        }
        tr:hover td { background-color: inherit; }
        .status-badge { font-size: 6.5pt; padding: 2px 8px; }
        li { font-size: 8.5pt; }
    }

    /* ===== EPC CARD + KPI ROW (Flex-based, WeasyPrint-friendly) ===== */
    .epc-card{
      background:#fff;
      border:4px solid;
      border-image: linear-gradient(135deg, #f5f5f5 0%, #606060 50%, #f5f5f5 100%) 1;
      border-radius:16px;
      box-shadow:
        0 3px 0 #60606033,
        0 6px 12px rgba(0,0,0,0.18),
        0 10px 25px rgba(0,0,0,0.12),
        inset 0 1px 0 rgba(255,255,255,0.6);
      padding:18px 18px 10px 18px;
      margin:18px 0 24px 0;
      overflow:hidden;
    }

    .epc-card .card-header{
      margin:0 0 12px 0;
      padding:10px 14px;
      border-radius:12px;
      background:
        linear-gradient(135deg, rgba(255,255,255,0.5) 0%, transparent 80%),
        linear-gradient(135deg, #f8fafc 0%, #cbd5e1 50%, #f8fafc 100%);
      border:4px solid;
      border-image: linear-gradient(90deg, #3b82f6 0%, #ffffff 3%, #808080 6%, #ffffff 9%, transparent 9%) 1;
      border-left-width:6px;
      box-shadow:0 3px 6px rgba(0,0,0,0.16), inset 0 2px 4px rgba(255,255,255,0.55);
    }

    .card-title{ margin:0; font-size:12pt; font-weight:400; text-transform:uppercase; letter-spacing:1px; color:#000; text-align:center; }
    .card-title .separator{ color:#3b82f6; font-weight:400; padding:0 8px; }
    .brand-jpmc{ font-weight:900; text-shadow:0 1px 0 rgba(255,255,255,0.6), 0 2px 6px rgba(0,0,0,0.25); letter-spacing:.2px; }

    .actions{
      background:#fff;
      border:3px solid;
      border-image: linear-gradient(135deg, #f5f5f5 0%, #606060 50%, #f5f5f5 100%) 1;
      border-radius:14px;
      padding:14px;
      box-shadow:0 2px 0 #60606033, 0 4px 10px rgba(0,0,0,0.12), 0 6px 15px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.6);
      margin-bottom:10px;
    }
    .action-item{ display:flex; gap:10px; align-items:flex-start; padding:8px 0; border-bottom:1px solid #d1d5db; }
    .action-item:last-child{ border-bottom:none; }
    .num{
      width:28px; height:28px; display:flex; align-items:center; justify-content:center;
      border:2px solid #d1d5db; border-radius:8px; font-weight:900; background:#f3f4f6;
      box-shadow:0 2px 4px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.5);
    }

    /* KPI row: flex with margin fallback */
    .grid-6{ display:flex; flex-wrap:wrap; margin: -8px; }
    .wide-110{ width:110%; margin-left:-5%; margin-right:-5%; padding:2px 0; overflow:hidden; box-sizing:border-box; }

    .tile{
      position:relative;
      background: linear-gradient(180deg, #ffffff 0%, #f9fafb 55%, #f3f4f6 100%);
      border-radius:18px;
      padding:18px 14px;
      text-align:center;
      min-height:165px;
      width: calc(16.66% - 16px);
      flex: 0 0 calc(16.66% - 16px);
      margin: 8px;
      outline:1px solid rgba(0,0,0,0.08);
      overflow:hidden;
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.9),
        inset 0 -1px 0 rgba(0,0,0,0.05),
        0 6px 12px rgba(0,0,0,0.10),
        0 12px 24px rgba(0,0,0,0.08);
      transition: transform .15s ease, box-shadow .15s ease;
    }
    .tile::before{
      content:""; position:absolute; left:0; right:0; top:0; height:38%;
      border-radius:18px 18px 0 0;
      background: linear-gradient(180deg, rgba(255,255,255,0.65) 0%, rgba(255,255,255,0.35) 40%, transparent 100%);
      pointer-events:none; mix-blend-mode:screen;
    }
    .tile:hover{
      transform: translateY(-2px);
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.95),
        inset 0 -1px 0 rgba(0,0,0,0.06),
        0 10px 18px rgba(0,0,0,0.12),
        0 20px 32px rgba(0,0,0,0.10);
    }
    .tile-kicker{ font-size:9pt; letter-spacing:1px; text-transform:uppercase; font-weight:900; color:#4b5563; margin-bottom:8px; }
    .tile-value{ font-size:28px; line-height:1; font-weight:900; color:#111827; margin-bottom:6px; text-shadow:0 1px 0 rgba(255,255,255,0.8), 0 2px 4px rgba(0,0,0,0.06); }
    .tile-sub{ color:#4b5563; font-size:9.5pt; }

    @media (max-width: 960px){ .tile{ flex:1 1 calc(33.33% - 16px); max-width:calc(33.33% - 16px); } }
    @media (max-width: 640px){ .tile{ flex:1 1 100%; max-width:100%; } }

    /* ===== Internal navigation (anchors) ===== */
    .local-nav{
        margin: 8px 0 6px 0;
        font-size: 8.5pt;
        font-weight: 700;
        color: var(--text-light);
    }
    .local-nav a{
        text-decoration: none;
        border-bottom: 1px dotted rgba(59,130,246,0.6);
        color: var(--accent);
    }
    .local-nav a:hover{ border-bottom-style: solid; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    @media print {
      .local-nav a { text-decoration: none; }
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
        '🟠': '<span class="status-badge badge-orange">ORG</span>',
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
        '💡': '',
        '🧾': '',
        '🧩': '',
        '🚨': '',
        '📉': '',
    }
    
    for emoji, replacement in replacements.items():
        html_content = html_content.replace(emoji, replacement)
    
    return html_content


# =============================
# 🔗 Internal Navigation Helpers (MINIMAL FIX - DON'T BREAK WORKING STUFF)
# =============================
import re
from typing import Set

def add_internal_navigation(html_body: str) -> str:
    """
    Inject internal navigation anchors (minimal + robust):
      - Ensure <a id="top"></a> at document start (once).
      - Insert <a id="pareto80"></a> immediately BEFORE the <h2> containing
        'SITES IN PARETO | 80%'.
      - Keep existing site anchors + local nav behavior.
      - Fix SITE column links to point at the correct #site-{LocationID}.
    """
    html = html_body

    # 1) Ensure top anchor is literally at the start
    if not re.match(r'\s*<a\s+id=["\']top["\']\s*></a>', html, flags=re.IGNORECASE):
        html = '<a id="top"></a>\n' + html

    # 2) Add Pareto-section anchor before the exact H2
    pareto_h2_block = re.compile(
        r'(?is)'
        r'(<h2[^>]*>\s*'
        r'(?:<span[^>]*>\s*)?'
        r'(?:📍|&#128205;)?\s*'
        r'SITES\s+IN\s+PARETO'
        r'(?:[^<]*?(?:\||&#124;)[^<]*?)'
        r'80%'
        r'\s*(?:</span>\s*)?'
        r'</h2>)'
    )
    if 'id="pareto80"' not in html and re.search(pareto_h2_block, html):
        html = re.sub(pareto_h2_block, lambda m: f'<a id="pareto80"></a>{m.group(1)}', html, count=1)

    # 3) Add site anchors for "📍 SITE X OF Y: Location N"
    #    IMPORTANT: stay within one <h2> by using [^<]* (do NOT use .*?)
    site_h2_re = re.compile(
        r'(?is)(<h2[^>]*>\s*[^<]*\bSITE\s+\d+\s+OF\s+\d+\s*:?\s*Location\s+(\d+)\s*[^<]*</h2>)'
    )
    site_ids: Set[str] = set()

    def _nav_block() -> str:
        return (
            '<div class="local-nav">'
            '<a href="#top">↑ Back to top</a> &nbsp;·&nbsp; '
            '<a href="#pareto80">↩ Back to Site Matrix</a>'
            '</div>'
        )

    def _add_site_anchor(m: re.Match) -> str:
        h2_block = m.group(1)
        loc_id = m.group(2)
        site_ids.add(loc_id)
        # Anchor BEFORE H2, nav block AFTER H2
        return f'<a id="site-{loc_id}"></a>{h2_block}{_nav_block()}'

    html = re.sub(site_h2_re, _add_site_anchor, html)

    # 4) Normalize any "Back to Site Matrix" link to #pareto80
    back_to_matrix = re.compile(r'(?is)<a\b[^>]*>(?:\s*↩\s*)?Back\s*to\s*Site\s*Matrix\s*</a>')
    def _force_href_to_pareto(match: re.Match) -> str:
        a_tag = match.group(0)
        if re.search(r'\bhref="[^"]*"', a_tag, flags=re.IGNORECASE):
            return re.sub(r'\bhref="[^"]*"', 'href="#pareto80"', a_tag, flags=re.IGNORECASE)
        return re.sub(r'<a\b', '<a href="#pareto80"', a_tag, flags=re.IGNORECASE)
    html = re.sub(back_to_matrix, _force_href_to_pareto, html)

    # 5) In the Pareto table, make the SITE column link to #site-{LocationID}
    if site_ids and 'id="pareto80"' in html:
        section_start = html.find('<a id="pareto80"></a>')
        if section_start != -1:
            m_next = re.search(r'<h2[^>]*>', html[section_start + 100:], flags=re.IGNORECASE)
            section_end = (section_start + 100 + m_next.start()) if m_next else len(html)
            section = html[section_start:section_end]

            # Only touch the first table in the Pareto section
            m_table = re.search(r'(?is)<table[^>]*>.*?</table>', section)
            if m_table:
                table = m_table.group(0)

                def _strip_tags(s: str) -> str:
                    return re.sub(r'<[^>]+>', '', s)

                # Find SITE column index from <thead>
                thead = re.search(r'(?is)<thead[^>]*>.*?</thead>', table)
                th_matches = list(re.finditer(r'(?is)<th[^>]*>(.*?)</th>', thead.group(0) if thead else table))
                site_col_idx = None
                header_col_count = len(th_matches)
                for idx, th_m in enumerate(th_matches):
                    if _strip_tags(th_m.group(1)).strip().upper() == 'SITE':
                        site_col_idx = idx
                        break

                if site_col_idx is not None:
                    def _fix_row(mrow: re.Match) -> str:
                        row_html = mrow.group(0)
                        if re.search(r'(?is)<th\b', row_html):  # skip header rows
                            return row_html
                        tds = list(re.finditer(r'(?is)(<td[^>]*>.*?</td>)', row_html))
                        if not tds:
                            return row_html

                        body_col_count = len(tds)
                        target_idx = site_col_idx
                        if body_col_count > header_col_count:
                            target_idx = site_col_idx + (body_col_count - header_col_count)
                        if not (0 <= target_idx < body_col_count):
                            return row_html

                        td_m = tds[target_idx]
                        td_html = td_m.group(1)
                        visible = _strip_tags(td_html).strip()
                        mnum = re.match(r'^(\d+)$', visible)
                        if not mnum:
                            return row_html
                        num = mnum.group(1)

                        # Fix existing anchor or wrap the number
                        def _retarget_anchor(a_m: re.Match) -> str:
                            a_tag = a_m.group(0)
                            if re.search(r'\bhref="[^"]*"', a_tag, flags=re.IGNORECASE):
                                return re.sub(r'\bhref="[^"]*"', f'href="#site-{num}"', a_tag, flags=re.IGNORECASE)
                            return re.sub(r'<a\b', f'<a href="#site-{num}"', a_tag, count=1, flags=re.IGNORECASE)

                        td_new, changed = re.subn(r'(?is)<a\b[^>]*>.*?</a>', _retarget_anchor, td_html, count=1)
                        if changed == 0:
                            td_new = re.sub(
                                r'(?is)(<td[^>]*>)\s*' + re.escape(num) + r'\s*(</td>)',
                                r'\1<a href="#site-' + num + r'">' + num + r'</a>\2',
                                td_html,
                                count=1
                            )

                        start, end = td_m.span(1)
                        return row_html[:start] + td_new + row_html[end:]

                    table = re.sub(r'(?is)<tr[^>]*>.*?</tr>', _fix_row, table)

                # splice table + section back
                section = section[:m_table.start()] + table + section[m_table.end():]
                html = html[:section_start] + section + html[section_end:]

    return html


# =============================
# 🔧 Utility Functions
# =============================

# ✅ FIXED: Timestamp function with fallback
def get_cst_timestamp(format_str: str = "%Y-%m-%d_%H-%M-%S") -> str:
    """
    Get current timestamp in CST timezone.
    Falls back through multiple methods to ensure CST.
    
    Args:
        format_str: strftime format string
    
    Returns:
        Formatted timestamp string in CST
    """
    if HAS_ZONEINFO:
        # Method 1: ZoneInfo (Python 3.9+)
        cst = ZoneInfo('America/Chicago')
        now_cst = datetime.now(cst)
        return now_cst.strftime(format_str)
    elif HAS_PYTZ:
        # Method 2: pytz (older Python or explicit install)
        cst = pytz.timezone('America/Chicago')
        now_cst = datetime.now(cst)
        return now_cst.strftime(format_str)
    else:
        # Method 3: Manual CST offset (UTC-6 standard, UTC-5 daylight)
        from datetime import timezone, timedelta
        cst_offset = timezone(timedelta(hours=-6))
        now_cst = datetime.now(cst_offset)
        return now_cst.strftime(format_str)


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

    # 🔗 Add anchors + nav links (keeps original content intact)
    html_body = add_internal_navigation(html_body)
    
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


def export_standard_report(
    report_id: str,
    format: str = 'html',
    output_dir: str = './reports',
    **kwargs
) -> str:
    """
    Generate and export a standard report.
    
    Args:
        report_id: Type of report ('site_health', 'customer_overview', 'region_overview', 'optimization_card', 'pareto_optimization')
        format: 'html' or 'pdf'
        output_dir: Directory to save the report
        **kwargs: Parameters for the report (customer_code, location_id, region, dates, etc.)
    
    Returns:
        Path to the generated file
    """
    
    # ✅ FIXED: Import directly from modular structure
    from .schedule_reports.reports import (
        generate_site_health,
        generate_customer_overview,
        generate_region_overview,
        generate_optimization_card,
        generate_pareto_optimization,
    )
    
    # ✅ Route to appropriate report function
    if report_id == 'site_health':
        if not all([kwargs.get('customer_code'), kwargs.get('location_id'), 
                    kwargs.get('start_date'), kwargs.get('end_date')]):
            raise ValueError("site_health requires: customer_code, location_id, start_date, end_date")
        markdown_content = generate_site_health(
            kwargs['customer_code'], 
            kwargs['location_id'], 
            kwargs['start_date'], 
            kwargs['end_date']
        )
    
    elif report_id == 'customer_overview':
        if not all([kwargs.get('customer_code'), kwargs.get('start_date'), kwargs.get('end_date')]):
            raise ValueError("customer_overview requires: customer_code, start_date, end_date")
        markdown_content = generate_customer_overview(
            kwargs['customer_code'], 
            kwargs['start_date'], 
            kwargs['end_date']
        )
    
    elif report_id == 'region_overview':
        if not all([kwargs.get('region'), kwargs.get('start_date'), kwargs.get('end_date')]):
            raise ValueError("region_overview requires: region, start_date, end_date")
        markdown_content = generate_region_overview(
            kwargs['region'], 
            kwargs['start_date'], 
            kwargs['end_date']
        )
    
    elif report_id == 'optimization_card':
        if not all([kwargs.get('customer_code'), kwargs.get('location_id'), 
                    kwargs.get('start_date'), kwargs.get('end_date')]):
            raise ValueError("optimization_card requires: customer_code, location_id, start_date, end_date")
        markdown_content = generate_optimization_card(
            kwargs['customer_code'], 
            kwargs['location_id'], 
            kwargs['start_date'], 
            kwargs['end_date']
        )
    
    elif report_id == 'pareto_optimization':
        if not all([kwargs.get('start_date'), kwargs.get('end_date'), kwargs.get('analysis_mode')]):
            raise ValueError("pareto_optimization requires: start_date, end_date, analysis_mode")
        
        if kwargs['analysis_mode'] not in ['customer', 'region']:
            raise ValueError("analysis_mode must be 'customer' or 'region'")
        
        if kwargs['analysis_mode'] == 'customer' and not kwargs.get('customer_code'):
            raise ValueError("customer_code required for customer mode")
        
        if kwargs['analysis_mode'] == 'region' and not kwargs.get('region'):
            raise ValueError("region required for region mode")
        
        markdown_content = generate_pareto_optimization(
            start_date=kwargs['start_date'],
            end_date=kwargs['end_date'],
            mode=kwargs['analysis_mode'],
            customer_code=kwargs.get('customer_code'),
            region=kwargs.get('region'),
            selected_locations=kwargs.get('selected_locations')
        )
    
    else:
        raise ValueError(
            f"Unknown report_id: {report_id}. "
            f"Available: site_health, customer_overview, region_overview, "
            f"optimization_card, pareto_optimization"
        )
    
    # ✅ Create descriptive filename
    timestamp = get_cst_timestamp("%Y-%m-%d_%H-%M-%S")
    
    if report_id == 'site_health':
        filename = f"site_health_{kwargs.get('customer_code')}_{kwargs.get('location_id')}_{timestamp}"
    elif report_id == 'customer_overview':
        filename = f"customer_overview_{kwargs.get('customer_code')}_{timestamp}"
    elif report_id == 'region_overview':
        filename = f"region_overview_{kwargs.get('region')}_{timestamp}"
    elif report_id == 'optimization_card':
        filename = f"optimization_card_{kwargs.get('customer_code')}_{kwargs.get('location_id')}_{timestamp}"
    elif report_id == 'pareto_optimization':
        analysis_mode = kwargs.get('analysis_mode', 'customer')
        if analysis_mode == 'region':
            region = kwargs.get('region', 'unknown')
            filename = f"pareto_optimization_region_{region}_{timestamp}"
        else:
            customer_code = kwargs.get('customer_code', 'unknown')
            filename = f"pareto_optimization_customer_{customer_code}_{timestamp}"
    else:
        filename = f"{report_id}_{timestamp}"
    
    # ✅ Export
    return export_report(markdown_content, format, output_dir, filename)


# =============================
# 🚀 HTML-BASED PARETO REPORTS
# =============================

def export_pareto_html_report(
    start_date: str,
    end_date: str,
    mode: str,
    format: str = 'html',
    output_dir: str = './reports',
    customer_code: Optional[int] = None,
    customer_name: Optional[str] = None,
    region: Optional[str] = None,
    selected_locations: Optional[List[str]] = None,
    filename: Optional[str] = None
) -> str:
    """
    Generate and export NEW HTML-based Pareto report (with interactive features).
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD) - used as week_ending_date
        mode: 'customer' or 'region'
        format: 'html' or 'pdf'
        output_dir: Directory to save report
        customer_code: Required for customer mode
        customer_name: Optional customer name (used for filename if provided)
        region: Required for region mode
        selected_locations: Optional list of location IDs
        filename: Optional custom filename (without extension)
    
    Returns:
        Path to generated file
    """
    from .schedule_reports.reports.pareto_optimization_html import generate_pareto_optimization_html
    
    # Validate inputs
    if mode == 'customer' and not customer_code:
        raise ValueError("customer_code required for customer mode")
    if mode == 'region' and not region:
        raise ValueError("region required for region mode")
    
    # Generate HTML content
    html_content = generate_pareto_optimization_html(
        start_date=start_date,
        end_date=end_date,
        mode=mode,
        customer_code=customer_code,
        region=region,
        selected_locations=selected_locations
    )
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # ✅ Generate standardized filename using filename_utils
    if not filename:
        if mode == 'customer':
            # Use customer_name if provided, otherwise fall back to customer_code
            identifier = customer_name if customer_name else str(customer_code)
            mode_label = 'Customer'
        else:
            identifier = region
            mode_label = 'Region'
        
        # Generate filename WITHOUT extension (we'll add it based on format)
        filename = generate_pareto_optimization_filename(
            mode=mode_label,
            scope_identifier=identifier,
            week_ending_date=end_date,
            extension=''  # No extension yet
        )
    
    # Export based on format
    if format.lower() == 'html':
        output_path = os.path.join(output_dir, f"{filename}.html")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return output_path
    
    elif format.lower() == 'pdf':
        output_path = os.path.join(output_dir, f"{filename}.pdf")
        html_to_pdf(html_content, output_path)
        return output_path
    
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'html' or 'pdf'")