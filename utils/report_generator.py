import os
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from utils.database import fetch_history

def generate_pdf_report(analysis_id: str, output_path: str = None) -> str:
    """
    Generates a professional executive PDF report for a given analysis record.
    """
    history = fetch_history()
    record = next((r for r in history if r["analysis_id"] == analysis_id), None)
    
    if not record:
        raise ValueError(f"Analysis record with ID {analysis_id} not found.")

    if not output_path:
        reports_dir = os.path.join("static", "reports")
        os.makedirs(reports_dir, exist_ok=True)
        output_path = os.path.join(reports_dir, f"Executive_Crowd_Report_{analysis_id[:8]}.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette matching web app neubrutalism / slate design
    PRIMARY = colors.HexColor("#0f172a")      # Dark Slate Body
    BLUE_ACCENT = colors.HexColor("#2563eb")  # Primary Blue
    BG_LIGHT = colors.HexColor("#f8fafc")     # Light Slate BG
    BORDER_COLOR = colors.HexColor("#cbd5e1") # Border Grey
    
    LEVEL_COLORS = {
        "Undercrowded": colors.HexColor("#10b981"),
        "Moderate": colors.HexColor("#f59e0b"),
        "Overcrowded": colors.HexColor("#ef4444")
    }

    crowd_level = record.get("crowd_level", "Moderate")
    level_color = LEVEL_COLORS.get(crowd_level, BLUE_ACCENT)

    # Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=PRIMARY
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=BLUE_ACCENT
    )

    h2_style = ParagraphStyle(
        'H2Style',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=PRIMARY,
        spaceBefore=10,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#334155")
    )

    bold_body = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    elements = []

    # 1. HEADER TABLE WITH LOGO
    logo_text_html = "<b>👥 MULTI-PERSPECTIVE CROWD DETECTION</b><br/><font color='#64748b' size=8>AI-Powered Spatial Density & Analytics Engine</font>"
    header_logo_p = Paragraph(logo_text_html, title_style)
    
    formatted_date = datetime.now().strftime("%B %d, %Y - %H:%M:%S")
    if record.get("timestamp"):
        try:
            dt = datetime.fromisoformat(record["timestamp"])
            formatted_date = dt.strftime("%B %d, %Y - %I:%M %p")
        except Exception:
            pass

    header_meta_html = f"<font size=8 color='#64748b'>REPORT REF:</font> <b>#{record['analysis_id'][:8]}</b><br/><font size=8 color='#64748b'>GENERATED:</font> <b>{formatted_date}</b>"
    header_meta_p = Paragraph(header_meta_html, ParagraphStyle('RightMeta', parent=body_style, alignment=2))

    header_table = Table([[header_logo_p, header_meta_p]], colWidths=[340, 200])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceBefore=4, spaceAfter=15))

    # 2. EXECUTIVE SUMMARY METRICS BANNER
    elements.append(Paragraph("EXECUTIVE CROWD ANALYSIS SUMMARY", subtitle_style))
    
    count_val = str(record.get("count", 0))
    density_val = f"{record.get('density', 0):.1f}%"
    reliability_val = f"{(record.get('reliability_score', 0) * 100):.0f}%"

    summary_data = [
        [
            Paragraph("<b>ESTIMATED CROWD COUNT</b>", ParagraphStyle('Cap', parent=body_style, fontSize=7, textColor=colors.HexColor("#64748b"))),
            Paragraph("<b>DENSITY PERCENTAGE</b>", ParagraphStyle('Cap', parent=body_style, fontSize=7, textColor=colors.HexColor("#64748b"))),
            Paragraph("<b>CROWD SAFETY LEVEL</b>", ParagraphStyle('Cap', parent=body_style, fontSize=7, textColor=colors.HexColor("#64748b"))),
            Paragraph("<b>RELIABILITY SCORE</b>", ParagraphStyle('Cap', parent=body_style, fontSize=7, textColor=colors.HexColor("#64748b"))),
        ],
        [
            Paragraph(f"<font size=18 color='#0f172a'><b>{count_val}</b></font> <font size=9 color='#64748b'>people</font>", body_style),
            Paragraph(f"<font size=18 color='#0f172a'><b>{density_val}</b></font>", body_style),
            Paragraph(f"<font size=14 color='{level_color.hexval()}'><b>{crowd_level.upper()}</b></font>", body_style),
            Paragraph(f"<font size=18 color='#2563eb'><b>{reliability_val}</b></font>", body_style),
        ]
    ]

    summary_table = Table(summary_data, colWidths=[135, 135, 135, 135])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 15))

    # 3. SPATIAL SYSTEM INSIGHTS & RELIABILITY METRICS
    elements.append(Paragraph("System Insights & Spatial Metrics", h2_style))
    
    views = record.get("per_image_details", {}).get("views", []) if record.get("per_image_details") else []
    first_view = views[0] if views else {}
    rel = first_view.get("reliability", {})

    avg_conf = f"{(rel.get('avg_confidence', 0.85) * 100):.1f}%" if rel.get('avg_confidence') else reliability_val
    small_ratio = f"{(rel.get('small_object_ratio', 0.15) * 100):.1f}%" if rel.get('small_object_ratio') is not None else "15.0%"
    occlusion = rel.get("occlusion_indicator", "Multi-View Consensus" if record.get("fusion_count") else "Standard Density")
    explanation = rel.get("explanation", f"Analysis completed on {formatted_date}. Total estimated headcount is {count_val} people at {density_val} density.")

    insights_data = [
        [Paragraph("<b>Average Confidence</b>", bold_body), Paragraph(avg_conf, body_style), Paragraph("<b>Small Object Ratio</b>", bold_body), Paragraph(small_ratio, body_style)],
        [Paragraph("<b>Occlusion Indicator</b>", bold_body), Paragraph(occlusion, body_style), Paragraph("<b>Consensus Strategy</b>", bold_body), Paragraph("Multi-Perspective Fusion" if record.get("fusion_count") else "Single Pass NMS_MERGE", body_style)],
        [Paragraph("<b>System Narrative</b>", bold_body), Paragraph(explanation, body_style), "", ""]
    ]

    insights_table = Table(insights_data, colWidths=[130, 140, 130, 140])
    insights_table.setStyle(TableStyle([
        ('SPAN', (1,2), (3,2)),
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(insights_table)
    elements.append(Spacer(1, 15))

    # 4. VISUAL DETECTION OUTPUT (Original vs Processed Images with Green Bounding Boxes)
    elements.append(Paragraph("Visual Detection Output", h2_style))
    
    if views:
        for idx, view in enumerate(views[:2]):
            orig_rel_url = view.get("original_url", "")
            proc_rel_url = view.get("processed_url", "")

            orig_path = os.path.join(os.getcwd(), orig_rel_url.lstrip("/\\"))
            proc_path = os.path.join(os.getcwd(), proc_rel_url.lstrip("/\\"))

            img_cells = []
            
            # Original Image
            if os.path.exists(orig_path):
                try:
                    img_cells.append(RLImage(orig_path, width=255, height=170))
                except Exception:
                    img_cells.append(Paragraph("<i>Original Image File Unavailable</i>", body_style))
            else:
                img_cells.append(Paragraph("<i>Original Image File Unavailable</i>", body_style))

            # Processed Image
            if os.path.exists(proc_path):
                try:
                    img_cells.append(RLImage(proc_path, width=255, height=170))
                except Exception:
                    img_cells.append(Paragraph("<i>Processed Image File Unavailable</i>", body_style))
            else:
                img_cells.append(Paragraph("<i>Processed Image File Unavailable</i>", body_style))

            label_text = f"Perspective View #{idx + 1}" if len(views) > 1 else "Primary Detection View"
            elements.append(Paragraph(f"<b>{label_text}</b>", ParagraphStyle('ViewTag', parent=body_style, fontSize=10, textColor=BLUE_ACCENT)))
            elements.append(Spacer(1, 4))

            img_table = Table([[img_cells[0], img_cells[1]]], colWidths=[265, 265])
            img_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
            ]))
            
            labels_row = [
                Paragraph("<b>ORIGINAL INPUT IMAGE</b>", ParagraphStyle('SubLbl', parent=body_style, alignment=1, fontSize=8, textColor=colors.HexColor("#64748b"))),
                Paragraph("<b>PROCESSED ANNOTATED DETECTIONS (YOLOv8x)</b>", ParagraphStyle('SubLbl', parent=body_style, alignment=1, fontSize=8, textColor=colors.HexColor("#64748b")))
            ]
            labels_table = Table([labels_row], colWidths=[265, 265])

            elements.append(KeepTogether([img_table, Spacer(1, 2), labels_table]))
            elements.append(Spacer(1, 12))

    # 5. AUTOMATED SAFETY RECOMMENDATIONS & ACTION PLAN
    elements.append(Spacer(1, 5))
    elements.append(Paragraph("Safety Assessment & Actionable Recommendations", h2_style))

    rec_title = ""
    rec_items = []
    
    if crowd_level == "Overcrowded":
        rec_title = "<font color='#ef4444'><b>ALERT: High Congestion / Overcrowded Threshold Reached</b></font>"
        rec_items = [
            "<b>Deploy Security Personnel:</b> Immediately dispatch security/station staff to regulate foot traffic near bottlenecks.",
            "<b>Open Auxiliary Exit Gates:</b> Activate secondary egress channels and exit turnstiles to accelerate crowd dissipation.",
            "<b>Platform Flow Restriction:</b> Temporarily hold incoming pedestrian streams at ticket barriers to prevent dangerous overcrowding."
        ]
    elif crowd_level == "Moderate":
        rec_title = "<font color='#f59e0b'><b>NOTICE: Moderate Crowd Density Observed</b></font>"
        rec_items = [
            "<b>Monitor Transit Points:</b> Keep automated monitoring active at escalators, stairwells, and main transit corridors.",
            "<b>Maintain Normal Operations:</b> Current density is manageable; maintain standard security post assignments.",
            "<b>Prepare Staging Gates:</b> Ensure secondary exit routes remain unlocked and unobstructed for peak period surges."
        ]
    else:
        rec_title = "<font color='#10b981'><b>NORMAL: Undercrowded / Optimal Safety Conditions</b></font>"
        rec_items = [
            "<b>Optimal Flow:</b> Pedestrian foot traffic is flowing freely with zero spatial congestion hazards.",
            "<b>Standard Monitoring:</b> Maintain baseline camera surveillance logs with zero intervention required."
        ]

    elements.append(Paragraph(rec_title, body_style))
    elements.append(Spacer(1, 4))
    
    for item in rec_items:
        elements.append(Paragraph(f"• {item}", ParagraphStyle('BulletItem', parent=body_style, leftIndent=12, spaceBefore=2)))

    # Footer Divider
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceBefore=10, spaceAfter=8))
    footer_text = Paragraph("<font size=7 color='#94a3b8'>CONFIDENTIAL EXECUTIVE REPORT • MULTI-PERSPECTIVE CROWD DENSITY ANALYTICS SYSTEM • AUTOMATED REPORT GENERATION</font>", ParagraphStyle('Foot', parent=body_style, alignment=1))
    elements.append(footer_text)

    # Build Document
    doc.build(elements)
    return output_path
