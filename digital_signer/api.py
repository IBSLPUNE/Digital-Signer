import frappe
import base64
from frappe.utils.pdf import get_pdf
import os
from io import BytesIO
from pyhanko.sign import signers, fields
from pyhanko.sign.signers import PdfSigner, PdfSignatureMetadata
from pyhanko.sign.fields import SigFieldSpec, append_signature_field
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.stamp import QRStampStyle
from PyPDF2 import PdfReader
import ast
from frappe import ValidationError
@frappe.whitelist()
def generate_invoice_pdf(doctype,docname):
    """Generate Sales Invoice PDF and return as base64"""
    try:
        doc = frappe.get_doc(doctype, docname)  # Get the Sales Invoice
        html = frappe.get_print(doctype, docname, print_format="Standard")
        pdf_data = get_pdf(html)

        # Convert PDF to base64
        pdf_base64 = base64.b64encode(pdf_data).decode("utf-8")
        return {"pdf": pdf_base64, "filename": f"{docname}.pdf"}

    except Exception as e:
        frappe.log_error(f"Error generating PDF: {str(e)}", "PDF Generation Error")
        return {"error": str(e)}







@frappe.whitelist()
def sign_sales_invoice_pdfs(doctype,sales_invoice_name, print_format_name=None, entered_password=None, multiple_page = None):
    """
    Generates the Sales Invoice PDF, digitally signs it page by page, and attaches it to the Sales Invoice.
    """
    sales_invoice = frappe.get_doc(doctype, sales_invoice_name)
    pdf_content = frappe.get_print(
        doctype,
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

    if int(multiple_page or 0) == 1:
        reader = IncrementalPdfFileWriter(input_pdf)
        #frappe.throw(f"hello {num_pages} and {multiple_page}")
        #frappe.throw(f'hello {num_pages}")
        #num_pages = len(reader.root['/Pages'].get_object()['/Kids'])

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
                reason=f"Digitally signed on {doctype}",
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
        #frappe.throw(f"{num_pages} and {multiple_page}")
        #num_pages = len(reader.root['/Pages'].get_object()['/Kids'])
        #frappe.throw(f'hello Lucky {num_pages}")
        output = BytesIO()

        sig_field_spec = SigFieldSpec(
            sig_field_name="Signature_Last_Page",
            box=(345, 50, 545, 100),
            on_page=num_pages - 1
        )
        append_signature_field(reader, sig_field_spec)

        signature_meta = PdfSignatureMetadata(
            field_name=sig_field_spec.sig_field_name,
            reason=f"Digitally signed on {doctype}",
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
        "attached_to_doctype": doctype,
        "attached_to_name": sales_invoice.name,
        "is_private": 1,
        "content": signed_pdf_io.getvalue(),
    })
    file_doc.insert(ignore_permissions=True)

    return "success"


@frappe.whitelist()
def sign_sales_invoice_pdf(doctype, sales_invoice_name, print_format_name=None, entered_password=None, multiple_page=None, page_range=None):
    try:
        sales_invoice = frappe.get_doc(doctype, sales_invoice_name)
        pdf_content = frappe.get_print(
            doctype,
            sales_invoice_name,
            print_format=print_format_name or "Digital Sign",
            as_pdf=True
        )

        digi = frappe.get_doc("Document Sign Setting")
        actual_password = digi.get_password('dsc_password')
        if entered_password != actual_password:
            frappe.throw("Password is wrong.")

        # Load signer
        if digi.pfx_file_use:
            pfx = digi.pfx_file
            if not pfx:
                frappe.throw("PFX not uploaded in Document Sign Setting.")
            pfx_file_path = frappe.get_site_path(digi.pfx_file.lstrip("/"))
            if not os.path.exists(pfx_file_path):
                frappe.throw(f"PFX file not found: {pfx_file_path}")
            try:
                signer = signers.SimpleSigner.load_pkcs12(
                    pfx_file_path,
                    passphrase=actual_password.encode()
                )
            except Exception:
                frappe.throw("Incorrect password for the DSC file.")
        else:
            cert = digi.certificate
            pvt = digi.private_key

            if not cert or not pvt:
                frappe.throw("Private Key or Certificate not uploaded in Document Sign Setting.")
            cert_path = frappe.get_site_path(digi.certificate.lstrip("/"))
            key_path = frappe.get_site_path(digi.private_key.lstrip("/"))
            if not os.path.exists(cert_path) or not os.path.exists(key_path):
                frappe.throw("Certificate or Private Key file not found on server.")
            signer = signers.SimpleSigner.load(key_path, cert_path)

        # Read and count pages
        input_pdf = BytesIO(pdf_content)
        reader = PdfReader(input_pdf)
        num_pages = len(reader.pages)
        input_pdf.seek(0)

        def parse_page_range(page_range_str, total_pages):
            result = set()
            if not page_range_str:
                return []
            parts = page_range_str.split(',')
            for part in parts:
                if '-' in part:
                    start, end = part.split('-')
                    start, end = int(start.strip()) - 1, int(end.strip()) - 1
                    result.update(range(start, end + 1))
                else:
                    result.add(int(part.strip()) - 1)
            return sorted(p for p in result if 0 <= p < total_pages)

        signed_pdf_io = input_pdf

        if int(multiple_page or 0) == 1:
            pages_to_sign = list(range(num_pages))
        elif page_range:
            pages_to_sign = parse_page_range(page_range, num_pages)
        else:
            pages_to_sign = [num_pages - 1]

        for i, page_num in enumerate(pages_to_sign):
            signed_pdf_io.seek(0)
            reader = IncrementalPdfFileWriter(signed_pdf_io)
            output = BytesIO()
            box = ast.literal_eval(digi.location) if digi.location else (345, 50, 545, 100)
            sig_field_spec = SigFieldSpec(
                sig_field_name=f"Signature_Page_{page_num + 1}",
                box=box,
                on_page=page_num
            )
            append_signature_field(reader, sig_field_spec)

            signature_meta = PdfSignatureMetadata(
                field_name=sig_field_spec.sig_field_name,
                reason=f"Digitally signed on {doctype}",
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
                appearance_text_params={'url': digi.url}
            )

            signed_pdf_io = output

        # Attach the signed PDF
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"{sales_invoice.name}-signed.pdf",
            "attached_to_doctype": doctype,
            "attached_to_name": sales_invoice.name,
            "is_private": 1,
            "content": signed_pdf_io.getvalue(),
        })
        file_doc.insert(ignore_permissions=True)

        return "success"

    except ValidationError:
        raise
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{doctype} Digital Sign Error")
        frappe.msgprint("Error log created.")
        frappe.throw("You entered an incorrect password in Document Sign Setting, or the PFX file is invalid. Please check the error log for more details.")


@frappe.whitelist()
def get_pdf_base64(doctype,name,print_format_name):
    pdf_content = frappe.get_print(doctype, name, print_format = print_format_name or "Digital Sign", as_pdf=True)
    return base64.b64encode(pdf_content).decode('utf-8')

@frappe.whitelist()
def save_signed_pdf(doctype,docname, signed_pdf_base64):
    file_path = f"/tmp/{docname}-signed.pdf"
    with open(file_path, "wb") as f:
        f.write(base64.b64decode(signed_pdf_base64))

    with open(file_path, "rb") as signed_file:
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"{docname}-signed.pdf",
            "attached_to_doctype": doctype,
            "attached_to_name": docname,
            "is_private": 1,
            "content": signed_file.read(),
        })
        file_doc.insert(ignore_permissions=True)
