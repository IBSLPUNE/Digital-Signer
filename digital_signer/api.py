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
from io import BytesIO
from PyPDF2 import PdfReader
from pyhanko.sign import signers, fields
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign.fields import SigFieldSpec, append_signature_field
from pyhanko.sign.signers import PdfSignatureMetadata
from pyhanko.stamp import QRStampStyle

@frappe.whitelist()
def sign_sales_invoice(sales_invoice_name, print_format_name):
    sales_invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)

    # Temporary file paths
    pdf_path = f"/tmp/{sales_invoice.name}.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Generate unsigned PDF
    pdf_content = frappe.get_print(
        "Sales Invoice",
        sales_invoice_name,
        print_format=print_format_name or "Digital Sign",
        as_pdf=True
    )

    # Save PDF
    with open(pdf_path, "wb") as f:
        f.write(pdf_content)

    # Load cert and key
    digi = frappe.get_doc("Document Sign Setting")
    cert = digi.certificate
    pvt = digi.private_key

    if not cert or not pvt:
        frappe.throw("Private Key or Certificate not uploaded in Document Sign Setting.")

    cert_path = frappe.get_site_path(cert.lstrip("/"))
    key_path = frappe.get_site_path(pvt.lstrip("/"))

    signer = signers.SimpleSigner.load(key_path, cert_path)

    # Count PDF pages
    reader = PdfReader(pdf_path)
    num_pages = len(reader.pages)

    # Prepare initial stream
    signed_pdf_io = BytesIO()
    signed_pdf_io.write(pdf_content)
    signed_pdf_io.seek(0)

    # Sign all pages (except last if needed)
    for i in range(num_pages):
        signed_pdf_io.seek(0)
        writer = IncrementalPdfFileWriter(signed_pdf_io)
        output = BytesIO()

        field_name = f"Signature_Page_{i+1}"
        visible_box = (345, 50, 545, 100)

        sig_field_spec = SigFieldSpec(
            sig_field_name=field_name,
            box=visible_box,
            on_page=i
        )
        append_signature_field(writer, sig_field_spec)

        signature_meta = PdfSignatureMetadata(
            field_name=field_name,
            reason="Digitally signed on Sales Invoice",
            location="Pune, Maharashtra, India"
        )

        qr_stamp = QRStampStyle(
            stamp_text="For: %(signer)s\nTime: %(ts)s"
        )

        appearance_text_params = {
            'url': 'https://bioprime.frappe.cloud/app'
        }

        pdf_signer = signers.PdfSigner(
            signature_meta,
            signer=signer,
            stamp_style=qr_stamp
        )

        pdf_signer.sign_pdf(
            writer,
            output=output,
            appearance_text_params=appearance_text_params
        )

        signed_pdf_io = output  # Update stream for next page

    # Final signed PDF is in signed_pdf_io
    signed_pdf_io.seek(0)
    signed_pdf_path = f"/tmp/{sales_invoice.name}-signed.pdf"
    with open(signed_pdf_path, "wb") as f:
        f.write(signed_pdf_io.read())

    # Attach to Sales Invoice
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
    return {"status": "success", "file_url": file_doc.file_url}

import frappe
import os
from io import BytesIO
from pyhanko.sign import signers
from pyhanko.sign.signers import PdfSigner, PdfSignatureMetadata
from pyhanko.sign.fields import SigFieldSpec, append_signature_field
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.stamp import QRStampStyle
from PyPDF2 import PdfReader

@frappe.whitelist()
def sign_sales_invoice_pdf(sales_invoice_name, print_format_name=None, entered_password=None, multiple_page_sign=None):
    """
    Generates the Sales Invoice PDF, digitally signs it page by page, and attaches it to the Sales Invoice.
    """
    sales_invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)
    pdf_content = frappe.get_print(
        "Sales Invoice",
        sales_invoice_name,
        print_format=print_format_name or "Digital Sign",
        as_pdf=True
    )

    # Load digital signing configuration
    digi = frappe.get_doc("Document Sign Setting")

    # Optional: Check entered password
    actual_password = digi.get_password('dsc_password')
    if entered_password != actual_password:
        frappe.throw("Password is wrong.")

    # Load signer from .pfx file
    if digi.pfx_file_use:
        pfx = digi.pfx_file
        if not pfx:
            frappe.throw("PFX not uploaded in Document Sign Setting.")
        pfx_file_path = frappe.get_site_path(digi.pfx_file.lstrip("/"))

        if not os.path.exists(pfx_file_path):
            frappe.throw(f"PFX file not found: {pfx_file_path}")

        signer = signers.SimpleSigner.load_pkcs12(
            pfx_file_path,
            signature_mechanism=None,
            passphrase=actual_password.encode()
        )

    # Load signer from certificate and private key
    else:
        cert = digi.certificate
        pvt = digi.private_key

        if not cert or not pvt:
            frappe.throw("Private Key or Certificate not uploaded in Document Sign Setting.")

        cert_path = frappe.get_site_path(cert.lstrip("/"))
        key_path = frappe.get_site_path(pvt.lstrip("/"))

        if not os.path.exists(cert_path) or not os.path.exists(key_path):
            frappe.throw("Certificate or Private Key file not found on server.")

        signer = signers.SimpleSigner.load(
            key_path,
            cert_path
        )


    # Add PDF signing logic here if needed.


    # Get page count
    input_pdf = BytesIO(pdf_content)
    num_pages = len(PdfReader(input_pdf).pages)
    input_pdf.seek(0)
    signed_pdf_io = input_pdf

    if digi.multiple_page_sign or multiple_page_sign:
        reader = IncrementalPdfFileWriter(input_pdf)
        num_pages = len(reader.root['/Pages'].get_object()['/Kids'])

        for i in range(num_pages):
            signed_pdf_io.seek(0)
            reader = IncrementalPdfFileWriter(signed_pdf_io)
            output = BytesIO()

            sig_field_spec = SigFieldSpec(
                sig_field_name=f"Signature_Page_{i+1}",
                box=(345, 50, 545, 100),
                on_page=i
            )
            append_signature_field(reader, sig_field_spec)

            signature_meta = PdfSignatureMetadata(
                field_name=sig_field_spec.sig_field_name,
                reason="Digitally signed on Sales Invoice",
                location=digi.sign_address or "India"
            )

            pdf_signer = PdfSigner(
                signature_meta,
                signer=signer,
                stamp_style=QRStampStyle(
                    stamp_text="For: %(signer)s\nTime: %(ts)s"
                )
            )

            pdf_signer.sign_pdf(
                reader,
                output=output,
                appearance_text_params={
                    'url': digi.url
                }
            )

            signed_pdf_io = output
    else:
        # Sign only the last page
        reader = IncrementalPdfFileWriter(input_pdf)
        num_pages = len(reader.root['/Pages'].get_object()['/Kids'])
        output = BytesIO()

        sig_field_spec = SigFieldSpec(
            sig_field_name="Signature_Last_Page",
            box=(345, 50, 545, 100),
            on_page=num_pages - 1
        )
        append_signature_field(reader, sig_field_spec)

        signature_meta = PdfSignatureMetadata(
            field_name=sig_field_spec.sig_field_name,
            reason="Digitally signed on Sales Invoice",
            location=digi.sign_address or "India"
        )

        pdf_signer = PdfSigner(
            signature_meta,
            signer=signer,
            stamp_style=QRStampStyle(
                stamp_text="For: %(signer)s\nTime: %(ts)s"
            )
        )

        pdf_signer.sign_pdf(
            reader,
            output=output,
            appearance_text_params={
                'url': digi.url
            }
        )

        signed_pdf_io = output

    # Attach signed PDF to the document
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": f"{sales_invoice.name}-signed.pdf",
        "attached_to_doctype": "Sales Invoice",
        "attached_to_name": sales_invoice.name,
        "is_private": 1,
        "content": signed_pdf_io.getvalue(),
    })
    file_doc.insert(ignore_permissions=True)

    return "success"



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
