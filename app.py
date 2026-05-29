from flask import Flask, render_template, request, send_file
from fpdf import FPDF
import io
import datetime
import os

_root = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    static_folder=os.path.join(_root, "static"),
    template_folder=os.path.join(_root, "templates"),
)

GREEN = (44, 74, 46)
LIGHT_GREEN = (244, 247, 244)
DARK = (26, 26, 26)
GREY = (120, 120, 120)
WHITE = (255, 255, 255)
BORDER = (220, 220, 220)


class QuotePDF(FPDF):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        d = self.data
        # Green top bar
        self.set_fill_color(*GREEN)
        self.rect(0, 0, 210, 22, "F")

        # Logo / brand name
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*WHITE)
        self.set_xy(15, 5)
        self.cell(80, 12, "NORDISKA KÖK", align="L")

        # Doc type + number
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*WHITE)
        self.set_xy(110, 4)
        self.cell(85, 5, d["doc_type"].upper(), align="R")
        self.set_xy(110, 9)
        self.cell(85, 5, f"# {d['doc_number']}   |   {d['date']}", align="R")
        if d["doc_type"] == "Quote":
            self.set_xy(110, 14)
            self.cell(85, 5, f"Valid until: {d['valid_until']}", align="R")

        self.ln(12)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*GREY)
        self.cell(0, 5,
                  "Nordiska Köket AB  ·  Kungsgatan 12, 111 43 Stockholm  ·  "
                  "info@nordiskakoket.se  ·  +46 8 000 00 00",
                  align="C")


def generate_pdf(data):
    pdf = QuotePDF(data)
    pdf.add_page()

    # --- From / To ---
    pdf.set_y(28)
    col_w = 85

    def section_header(label):
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*GREY)
        pdf.cell(col_w, 5, label.upper(), ln=False)

    # From column
    x_from = 15
    x_to = 110
    y_info = pdf.get_y()

    pdf.set_xy(x_from, y_info)
    section_header("From")
    pdf.set_xy(x_to, y_info)
    section_header("To")
    pdf.ln(6)

    # Thin rule
    pdf.set_draw_color(*BORDER)
    pdf.line(x_from, pdf.get_y(), x_from + col_w, pdf.get_y())
    pdf.line(x_to, pdf.get_y(), x_to + col_w, pdf.get_y())
    pdf.ln(3)

    from_lines = [
        ("B", "Nordiska Köket AB"),
        ("", "Kungsgatan 12"),
        ("", "111 43 Stockholm"),
        ("", "info@nordiskakoket.se"),
        ("", "+46 8 000 00 00"),
    ]
    to_lines = [
        ("B", data["customer_name"]),
        ("", data["customer_address"]),
        ("", data["customer_city"]),
        ("", data["customer_email"]),
        ("", data["customer_phone"]),
    ]

    y_after = pdf.get_y()
    for style, text in from_lines:
        if text:
            pdf.set_xy(x_from, y_after)
            pdf.set_font("Helvetica", style, 9)
            pdf.set_text_color(*DARK)
            pdf.cell(col_w, 5, text)
            y_after += 5

    y_after2 = pdf.get_y() - (len([t for _, t in from_lines if t]) * 5)
    for style, text in to_lines:
        if text:
            pdf.set_xy(x_to, y_after2)
            pdf.set_font("Helvetica", style, 9)
            pdf.set_text_color(*DARK)
            pdf.cell(col_w, 5, text)
            y_after2 += 5

    pdf.set_y(max(y_after, y_after2) + 6)

    # --- Project badge ---
    if data["project_name"]:
        pdf.set_fill_color(*LIGHT_GREEN)
        pdf.set_draw_color(*GREEN)
        pdf.set_line_width(0.8)
        y_badge = pdf.get_y()
        pdf.rect(15, y_badge, 180, 8, "FD")
        pdf.set_line_width(0.2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*GREEN)
        pdf.set_xy(19, y_badge + 1.5)
        pdf.cell(20, 5, "Project:")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*DARK)
        pdf.cell(155, 5, data["project_name"])
        pdf.ln(12)

    # --- Items table ---
    headers = ["Item", "Description", "Qty", "Unit Price", "Total"]
    col_widths = [42, 58, 18, 32, 30]

    # Table header row
    pdf.set_fill_color(*GREEN)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 8)
    for header, w in zip(headers, col_widths):
        align = "R" if header in ("Qty", "Unit Price", "Total") else "L"
        pdf.cell(w, 8, header, border=0, align=align, fill=True)
    pdf.ln()

    # Table rows
    pdf.set_font("Helvetica", "", 9)
    for i, item in enumerate(data["items"]):
        fill = (i % 2 == 1)
        pdf.set_fill_color(*LIGHT_GREEN)
        pdf.set_text_color(*DARK)
        row_h = 7
        row_data = [
            item["name"],
            item["desc"],
            f"{item['qty']:.0f}",
            f"{item['price']:,.2f} SEK",
            f"{item['total']:,.2f} SEK",
        ]
        for val, w in zip(row_data, col_widths):
            align = "R" if w <= 32 and val != item["name"] and val != item["desc"] else "L"
            pdf.cell(w, row_h, val, border=0, align=align, fill=fill)
        pdf.ln()

    # Bottom line
    pdf.set_draw_color(*GREEN)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(4)

    # --- Totals ---
    x_totals = 130
    def total_row(label, amount, bold=False):
        pdf.set_font("Helvetica", "B" if bold else "", 9 if not bold else 11)
        pdf.set_text_color(*GREEN if bold else DARK)
        pdf.set_x(x_totals)
        pdf.cell(40, 6, label, align="L")
        pdf.cell(25, 6, f"{amount:,.2f} SEK", align="R")
        pdf.ln()

    total_row("Subtotal", data["subtotal"])
    total_row("VAT (25%)", data["vat"])
    pdf.set_x(x_totals)
    pdf.set_draw_color(*GREEN)
    pdf.set_line_width(0.8)
    pdf.line(x_totals, pdf.get_y(), 195, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(2)
    total_row("Total", data["grand_total"], bold=True)
    pdf.ln(6)

    # --- Notes ---
    if data["notes"]:
        pdf.set_fill_color(*LIGHT_GREEN)
        pdf.set_draw_color(*BORDER)
        y_n = pdf.get_y()
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*GREY)
        pdf.cell(180, 5, "NOTES & TERMS", ln=True)
        pdf.set_draw_color(*BORDER)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(180, 5, data["notes"])
        pdf.ln(6)

    # --- Signatures ---
    sig_y = pdf.get_y() + 4
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*GREY)
    pdf.set_xy(15, sig_y)
    pdf.cell(85, 5, "APPROVED BY — NORDISKA KÖK", align="C")
    pdf.set_xy(110, sig_y)
    pdf.cell(85, 5, "APPROVED BY — CUSTOMER", align="C")

    sig_line_y = sig_y + 18
    pdf.set_draw_color(*GREY)
    pdf.line(15, sig_line_y, 95, sig_line_y)
    pdf.line(110, sig_line_y, 190, sig_line_y)

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*GREY)
    pdf.set_xy(15, sig_line_y + 2)
    pdf.cell(85, 5, "Signature & Date", align="C")
    pdf.set_xy(110, sig_line_y + 2)
    pdf.cell(85, 5, "Signature & Date", align="C")

    return pdf.output()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/preview", methods=["POST"])
def preview():
    data = build_data(request.form)
    return render_template("pdf_template.html", **data)


@app.route("/generate", methods=["POST"])
def generate():
    data = build_data(request.form)
    pdf_bytes = generate_pdf(data)
    filename = f"quote_{data['doc_number']}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


def build_data(form):
    items = []
    names = form.getlist("item_name[]")
    descs = form.getlist("item_desc[]")
    qtys = form.getlist("item_qty[]")
    prices = form.getlist("item_price[]")

    subtotal = 0.0
    for name, desc, qty, price in zip(names, descs, qtys, prices):
        if name.strip():
            qty_f = float(qty or 0)
            price_f = float(price or 0)
            total = qty_f * price_f
            subtotal += total
            items.append({
                "name": name,
                "desc": desc,
                "qty": qty_f,
                "price": price_f,
                "total": total,
            })

    vat_rate = 0.25
    vat = subtotal * vat_rate
    grand_total = subtotal + vat

    doc_type = form.get("doc_type", "Quote")
    today = datetime.date.today()
    valid_until = today + datetime.timedelta(days=30)

    return {
        "doc_type": doc_type,
        "doc_number": form.get("doc_number", "001"),
        "date": today.strftime("%Y-%m-%d"),
        "valid_until": valid_until.strftime("%Y-%m-%d"),
        "customer_name": form.get("customer_name", ""),
        "customer_address": form.get("customer_address", ""),
        "customer_city": form.get("customer_city", ""),
        "customer_phone": form.get("customer_phone", ""),
        "customer_email": form.get("customer_email", ""),
        "project_name": form.get("project_name", ""),
        "notes": form.get("notes", ""),
        "items": items,
        "subtotal": subtotal,
        "vat": vat,
        "grand_total": grand_total,
    }


if __name__ == "__main__":
    app.run(debug=True)
