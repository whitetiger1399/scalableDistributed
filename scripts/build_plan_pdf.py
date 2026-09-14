#!/usr/bin/env python3
"""Render the registered randomized experiment plan as a reviewable PDF."""
import html
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/randomized-experiment-plan.md"
OUTPUT = ROOT / "report/Randomized_Experiment_Plan.pdf"


def inline(value):
    # Keep URLs and Markdown markers readable in a plain-text plan PDF.
    return html.escape(value.replace("<!-- pagebreak -->", ""))


def main():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="PlanBody", parent=styles["BodyText"], fontSize=9.2,
                              leading=12.2, spaceAfter=6, textColor=colors.HexColor("#243247")))
    styles.add(ParagraphStyle(name="PlanH1", parent=styles["Heading1"], fontSize=17,
                              leading=20, spaceBefore=10, spaceAfter=8, textColor=colors.HexColor("#142e4c")))
    styles.add(ParagraphStyle(name="PlanH2", parent=styles["Heading2"], fontSize=12,
                              leading=15, spaceBefore=7, spaceAfter=5, textColor=colors.HexColor("#235c8f")))
    styles.add(ParagraphStyle(name="PlanCode", parent=styles["Code"], fontSize=8.2,
                              leading=10, leftIndent=10, spaceAfter=5))
    styles.add(ParagraphStyle(name="PlanSubtitle", parent=styles["BodyText"], fontSize=12,
                              leading=15, textColor=colors.HexColor("#536778"), spaceAfter=8))
    story = [Paragraph("Randomized Cassandra Consistency Experiments", styles["Title"]),
             Paragraph("Registered redesign plan and reproducibility protocol", styles["PlanSubtitle"]), Spacer(1, 10)]
    in_code = False
    for raw in SOURCE.read_text().splitlines():
        line = raw.rstrip()
        if line.strip() == "<!-- pagebreak -->":
            story.append(PageBreak())
            continue
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            story.append(Paragraph(inline(line) or " ", styles["PlanCode"]))
        elif line.startswith("### "):
            story.append(Paragraph(inline(line[4:]), styles["PlanH2"]))
        elif line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), styles["PlanH1"]))
        elif line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), styles["PlanH1"]))
        elif line.startswith("| ") or line.startswith("- ") or line.startswith("1. ") or line.startswith("2. ") or line.startswith("3. ") or line.startswith("4. ") or line.startswith("5. ") or line.startswith("6. ") or line.startswith("7. ") or line.startswith("8. ") or line.startswith("9. "):
            story.append(Paragraph(inline(line), styles["PlanBody"]))
        elif line:
            story.append(Paragraph(inline(line), styles["PlanBody"]))
        else:
            story.append(Spacer(1, 3))

    def footer(canvas, document):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#536778"))
        canvas.drawString(48, 28, "Randomized Cassandra experiment plan")
        canvas.drawRightString(A4[0] - 48, 28, str(document.page))

    SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=48, rightMargin=48,
                      topMargin=42, bottomMargin=48,
                      title="Randomized Cassandra Consistency Experiments").build(
                          story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
