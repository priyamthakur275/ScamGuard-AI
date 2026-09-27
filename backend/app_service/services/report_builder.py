"""Exportable report generation (Phase 12).

Every value in a generated report is read directly from an already-
computed AnalysisResult (or list of them, for a case) -- this module
performs no analysis of its own and invents nothing. Its only job is
formatting real data for JSON/CSV/PDF export.

Semantic separation is enforced by construction: model_probability,
confidence, and threat_score are always three distinct, separately
labeled fields in every export format below -- never merged, relabeled,
or substituted for one another.
"""
import csv
import io
import json
from datetime import datetime, timezone

from app_service.schemas.message import AnalysisResult


def build_scan_report_data(scan: AnalysisResult) -> dict:
    """The one canonical structured representation of a scan's report
    data, shared by all three export formats below so they can never
    drift out of sync with each other.
    """
    metadata = scan.metadata or {}
    return {
        "scan_id": str(scan.id),
        "timestamp": scan.created_at.isoformat() if isinstance(scan.created_at, datetime) else str(scan.created_at),
        "input_type": scan.input_type,
        "verdict": scan.verdict,
        "model_name": scan.model_name,
        "model_version": scan.model_version,
        # Kept as three explicitly distinct fields -- never merged.
        "model_probability": scan.scam_probability,
        "confidence": scan.confidence_score,
        "threat_score": scan.threat_score,
        "risk_level": scan.risk_level,
        "category": scan.scam_category,
        "evidence": {
            "ml_contributing_tokens": [
                {"token": t.token, "weight": t.weight} for t in scan.top_contributing_tokens
            ],
            "risk_breakdown": scan.risk_breakdown or {},
        },
        "entities": scan.highlighted_entities or {},
        "url_email_intelligence": {
            "url_intelligence": metadata.get("url_intelligence"),
            "email_forensics": metadata.get("email_forensics"),
            "voice_evidence": metadata.get("voice_evidence"),
        },
        "xai": {
            "executive_summary": scan.executive_summary,
            "technical_explanation": scan.technical_explanation,
            "ai_explanation": scan.ai_explanation,
        },
        "recommendations": scan.recommended_actions or [],
        "user_feedback": scan.user_feedback,
    }


def build_case_report_data(case_id: str, title: str, status: str, scans: list[AnalysisResult]) -> dict:
    return {
        "case_id": case_id,
        "case_title": title,
        "case_status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scan_count": len(scans),
        "scans": [build_scan_report_data(s) for s in scans],
    }


def to_json_bytes(report_data: dict) -> bytes:
    return json.dumps(report_data, indent=2, default=str).encode("utf-8")


_CSV_COLUMNS = [
    "scan_id", "timestamp", "input_type", "verdict", "model_name", "model_version",
    "model_probability", "confidence", "threat_score", "risk_level", "category",
    "ml_contributing_tokens", "risk_breakdown", "entities", "url_email_intelligence",
    "executive_summary", "recommendations",
]


def _flatten_for_csv(scan_report: dict) -> dict:
    return {
        "scan_id": scan_report["scan_id"],
        "timestamp": scan_report["timestamp"],
        "input_type": scan_report["input_type"],
        "verdict": scan_report["verdict"],
        "model_name": scan_report["model_name"],
        "model_version": scan_report["model_version"],
        "model_probability": scan_report["model_probability"],
        "confidence": scan_report["confidence"],
        "threat_score": scan_report["threat_score"],
        "risk_level": scan_report["risk_level"],
        "category": scan_report["category"] or "",
        "ml_contributing_tokens": json.dumps(scan_report["evidence"]["ml_contributing_tokens"]),
        "risk_breakdown": json.dumps(scan_report["evidence"]["risk_breakdown"]),
        "entities": json.dumps(scan_report["entities"]),
        "url_email_intelligence": json.dumps(
            {k: v for k, v in scan_report["url_email_intelligence"].items() if v is not None}
        ),
        "executive_summary": scan_report["xai"]["executive_summary"] or "",
        "recommendations": json.dumps(scan_report["recommendations"]),
    }


def to_csv_bytes(scan_reports: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_CSV_COLUMNS)
    writer.writeheader()
    for scan_report in scan_reports:
        writer.writerow(_flatten_for_csv(scan_report))
    return buffer.getvalue().encode("utf-8")


def to_pdf_bytes(scan_reports: list[dict], report_title: str) -> bytes:
    """Uses reportlab (a well-established, pure-Python PDF library, no
    system dependencies) to lay out a real, readable report -- not a
    minimal/placeholder PDF. Model probability, confidence, and threat
    score are always rendered as three separate labeled rows, never
    combined into one number.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], fontSize=18)
    heading_style = ParagraphStyle("SectionHeading", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6)
    body_style = styles["BodyText"]

    story = [Paragraph(report_title, title_style), Spacer(1, 0.2 * inch)]

    for i, scan_report in enumerate(scan_reports):
        if i > 0:
            story.append(PageBreak())

        story.append(Paragraph(f"Scan {scan_report['scan_id']}", heading_style))

        metrics_table = Table(
            [
                ["Timestamp", scan_report["timestamp"]],
                ["Input type", scan_report["input_type"]],
                ["Verdict", scan_report["verdict"]],
                ["Model", f"{scan_report['model_name']} (v{scan_report['model_version']})"],
                ["Model probability", f"{scan_report['model_probability']:.2%}"],
                ["Confidence", f"{scan_report['confidence']:.2%}"],
                ["Threat score", f"{scan_report['threat_score']:.2%}"],
                ["Risk level", scan_report["risk_level"]],
                ["Category", scan_report["category"] or "Uncategorized"],
            ],
            colWidths=[1.8 * inch, 4.2 * inch],
        )
        metrics_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 0.15 * inch))

        if scan_report["xai"]["executive_summary"]:
            story.append(Paragraph("Explanation", heading_style))
            story.append(Paragraph(scan_report["xai"]["executive_summary"], body_style))

        tokens = scan_report["evidence"]["ml_contributing_tokens"]
        if tokens:
            story.append(Paragraph("ML evidence (contributing tokens)", heading_style))
            story.append(Paragraph(
                ", ".join(f"{t['token']} ({t['weight']:.2f})" for t in tokens), body_style
            ))

        entities = scan_report["entities"]
        entity_lines = [f"{k}: {', '.join(v)}" for k, v in entities.items() if v]
        if entity_lines:
            story.append(Paragraph("Entities", heading_style))
            for line in entity_lines:
                story.append(Paragraph(line, body_style))

        recs = scan_report["recommendations"]
        if recs:
            story.append(Paragraph("Recommendations", heading_style))
            for rec in recs:
                story.append(Paragraph(f"• {rec}", body_style))

    doc.build(story)
    return buffer.getvalue()
