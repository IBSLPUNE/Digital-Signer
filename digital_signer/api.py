import frappe
import base64
from frappe.utils.pdf import get_pdf

@frappe.whitelist()
def generate_invoice_pdf(docname):
    """Generate Sales Invoice PDF and return as base64"""
    try:
        doc = frappe.get_doc("Sales Invoice", docname)  # Get the Sales Invoice
        html = frappe.get_print("Sales Invoice", docname, print_format="Standard")
        pdf_data = get_pdf(html)

        # Convert PDF to base64
        pdf_base64 = base64.b64encode(pdf_data).decode("utf-8")
        return {"pdf": pdf_base64, "filename": f"{docname}.pdf"}

    except Exception as e:
        frappe.log_error(f"Error generating PDF: {str(e)}", "PDF Generation Error")
        return {"error": str(e)}
import frappe
import os
from pyhanko.sign import signers, fields
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

@frappe.whitelist()
def sign_sales_invoice_pdf(sales_invoice_name, print_format_name):
    """
    Generates the Sales Invoice PDF, digitally signs it, and attaches it to the Sales Invoice.
    """

    # Fetch the Sales Invoice
    sales_invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)

    # Prepare file paths
    pdf_path = f"/tmp/{sales_invoice.name}.pdf"
    signed_pdf_path = f"/tmp/{sales_invoice.name}-signed.pdf"

    # Ensure target directory exists
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Generate the PDF content
    pdf_content = frappe.get_print(
        "Sales Invoice",
        sales_invoice_name,
        print_format=print_format_name or "Digital SIgn",
        as_pdf=True
    )

    # Write the original PDF to file
    with open(pdf_path, "wb") as pdf_file:
        pdf_file.write(pdf_content)

    # Get certificate and private key from Document Sign Setting
    digi = frappe.get_doc("Document Sign Setting")
    cert = digi.certificate
    pvt = digi.private_key

    if not cert or not pvt:
        frappe.throw("Private Key or Certificate not uploaded in Document Sign Setting.")

    certificate_path = frappe.get_site_path(cert.lstrip("/"))
    private_key_path = frappe.get_site_path(pvt.lstrip("/"))

    # Load signer
    signer = signers.SimpleSigner.load(private_key_path, certificate_path)

    # Signature field name and box location (x1, y1, x2, y2)
    signature_field_name = "Signature"
    box = (420, 80, 550, 135)

    # Sign the PDF
    with open(pdf_path, "rb") as inf:
        w = IncrementalPdfFileWriter(inf)

        # Add signature field to the PDF
        fields.append_signature_field(w, sig_field_spec=fields.SigFieldSpec(signature_field_name, box=box))

        # Create signature metadata
        meta = signers.PdfSignatureMetadata(
            field_name=signature_field_name,
            reason=f"Digitally signed on {(frappe.utils.now_datetime()).strftime('%d-%m-%Y %H:%M:%S')} IST",
            location="Pune, Maharashtra, India"
        )

        # Create PDF signer
        pdf_signer = signers.PdfSigner(meta, signer=signer, stamp_style=None)

        # Write signed PDF
        with open(signed_pdf_path, "wb") as outf:
            pdf_signer.sign_pdf(w, output=outf)

    # Attach the signed PDF to the Sales Invoice
    with open(signed_pdf_path, "rb") as signed_file:
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"{sales_invoice.name}-signed.pdf",
            "attached_to_doctype": "Sales Invoice",
            "attached_to_name": sales_invoice.name,
            "is_private": 1,
            "content": signed_file.read(),
        })
        file_doc.insert(ignore_permissions=True)

    frappe.msgprint(f"Signed PDF successfully attached to Sales Invoice {sales_invoice.name}.")
    return signed_pdf_path



@frappe.whitelist()
def get_pdf_base64(name,print_format_name):
    pdf_content = frappe.get_print("Sales Invoice", name, print_format = print_format_name or "Digital Sign", as_pdf=True)
    return base64.b64encode(pdf_content).decode('utf-8')

@frappe.whitelist()
def save_signed_pdf(docname, signed_pdf_base64):
    file_path = f"/tmp/{docname}-signed.pdf"
    with open(file_path, "wb") as f:
        f.write(base64.b64decode(signed_pdf_base64))

    with open(file_path, "rb") as signed_file:
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"{docname}-signed.pdf",
            "attached_to_doctype": "Sales Invoice",
            "attached_to_name": docname,
            "is_private": 1,
            "content": signed_file.read(),
        })
        file_doc.insert(ignore_permissions=True)
