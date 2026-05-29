from flask import Flask, render_template, request, send_file
from weasyprint import HTML
import io
import datetime

app = Flask(__name__)


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
    html_content = render_template("pdf_template.html", **data)
    pdf = HTML(string=html_content, base_url=request.host_url).write_pdf()
    filename = f"quote_{data['doc_number']}.pdf"
    return send_file(
        io.BytesIO(pdf),
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
