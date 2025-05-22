import frappe
import os
from io import BytesIO
import json
from pyhanko.sign import signers
from pyhanko.sign.signers import PdfSigner, PdfSignatureMetadata
from pyhanko.sign.fields import SigFieldSpec, append_signature_field
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.stamp import QRStampStyle
from PyPDF2 import PdfReader
from frappe import ValidationError
@frappe.whitelist()
def sign_sales_invoice_pdfs(doctype,sales_invoice_name, print_format_name=None, entered_password=None, x=0, y=0, page_range=None):
    try:
        # Get Sales Invoice Doc
        sales_invoice = frappe.get_doc(doctype, sales_invoice_name)

        # Get PDF content of Sales Invoice
        pdf_content = frappe.get_print(
            doctype,
            sales_invoice_name,
            print_format=print_format_name or "Digital Sign",
            as_pdf=True
        )

        # Get Document Sign Setting doc for DSC details
        digi = frappe.get_doc("Document Sign Setting")
        actual_password = digi.get_password('dsc_password')

        if entered_password != actual_password:
            frappe.throw("Password is wrong.")

        # Load signer from PFX or cert/key files
        if digi.pfx_file_use:
            pfx_file_path = frappe.get_site_path(digi.pfx_file.lstrip("/"))
            if not os.path.exists(pfx_file_path):
                frappe.throw(f"PFX file not found: {pfx_file_path}")
            signer = signers.SimpleSigner.load_pkcs12(
                pfx_file_path,
                signature_mechanism=None,
                passphrase=actual_password.encode()
            )
        else:
            cert_path = frappe.get_site_path(digi.certificate.lstrip("/"))
            key_path = frappe.get_site_path(digi.private_key.lstrip("/"))
            if not os.path.exists(cert_path) or not os.path.exists(key_path):
                frappe.throw("Certificate or Private Key file not found on server.")
            signer = signers.SimpleSigner.load(
                key_path,
                cert_path
            )

        # Load PDF and get page count
        input_pdf_io = BytesIO(pdf_content)
        pdf_reader = PdfReader(input_pdf_io)
        num_pages = len(pdf_reader.pages)

        # Validate page number received from frontend (1-based)
        try:
            page_num = int(page_range or 1) - 1  # zero-based
            #frappe.throw(f"Page number {page_num + float(x)} is out of range for the PDF.")
        except Exception:
            page_num = 0

        if page_num < 0 or page_num >= num_pages:
            frappe.throw(f"Page number {page_num + 1} is out of range for the PDF.")

        # Prepare incremental writer
        input_pdf_io.seek(0)
        reader = IncrementalPdfFileWriter(input_pdf_io)

        # Signature box coordinates (x,y) are from the frontend click.
        # You can adjust width and height as needed.
        # Here we create a rectangle from (x,y) bottom-left to (x+width, y+height)
        sig_width = 200
        sig_height = 50
        sig_box = (float(x), float(y), float(x) + sig_width, float(y) + sig_height)
        #frappe.throw(f"Page number {sig_box} is out of range for the PDF.")
        # Append signature field to specified page at clicked location
        sig_field_spec = SigFieldSpec(
            sig_field_name=f"Signature_Page_{page_num + 1}",
            box=sig_box,
            on_page=page_num
        )
        append_signature_field(reader, sig_field_spec)

        # Signature metadata
        signature_meta = PdfSignatureMetadata(
            field_name=sig_field_spec.sig_field_name,
            reason=f"Digitally signed on {doctype}",
            location=digi.sign_address or "India"
        )

        # Setup signer with QR stamp style
        pdf_signer = PdfSigner(
            signature_meta,
            signer=signer,
            stamp_style=QRStampStyle(
                stamp_text="For: %(signer)s\nTime: %(ts)s"
            )
        )

        output = BytesIO()
        pdf_signer.sign_pdf(
            reader,
            output=output,
            appearance_text_params={'url': digi.url}
        )

        # Save signed PDF as private attachment to Sales Invoice
        output.seek(0)
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"{sales_invoice.name}-signed.pdf",
            "attached_to_doctype": doctype,
            "attached_to_name": sales_invoice.name,
            "is_private": 1,
            "content": output.getvalue(),
            "decode": False,
        })
        file_doc.insert(ignore_permissions=True)

        return "success"

    except ValidationError:
        raise
    except Exception as e:
        frappe.log_error(f"Error in sign_sales_invoice_pdf: {str(e)}", "{doctype} PDF Signing")
        frappe.throw(f"Failed to sign PDF: {str(e)}")
# Python (Frappe Backend) - sign_sales_invoice_pdfs


@frappe.whitelist()
def sign_sales_invoice_pdf(doctype,sales_invoice_name, print_format_name=None, entered_password=None, coordinates_json=None):
    try:
        sales_invoice = frappe.get_doc(doctype, sales_invoice_name)

        pdf_content = frappe.get_print(
            doctype,
            sales_invoice_name,
            print_format=print_format_name or "Standard",
            as_pdf=True
        )

        digi = frappe.get_doc("Document Sign Setting")
        actual_password = digi.get_password('dsc_password')
        if entered_password != actual_password:
            frappe.throw("Password is wrong.")

        if digi.pfx_file_use:
            pfx = digi.pfx_file
            if not pfx:
            	frappe.throw("PFX not uploaded in Document Sign Setting.")
            pfx_file_path = frappe.get_site_path(digi.pfx_file.lstrip("/"))
            try:
                signer = signers.SimpleSigner.load_pkcs12(
                    pfx_file_path,
                    passphrase=actual_password.encode()
                )
            except Exception as e:
                frappe.throw("Incorrect password for the DSC file.")
        else:
            cert = digi.certificate
            pvt = digi.private_key
            if not cert or not pvt:
            	frappe.throw("Private Key or Certificate not uploaded in Document Sign Setting.")
            cert_path = frappe.get_site_path(digi.certificate.lstrip("/"))
            key_path = frappe.get_site_path(digi.private_key.lstrip("/"))
            signer = signers.SimpleSigner.load(
                key_path,
                cert_path
            )

        coordinates = json.loads(coordinates_json or "[]")
        if not coordinates:
            frappe.throw("No signature coordinates provided.")

        input_pdf_io = BytesIO(pdf_content)
        pdf_reader = PdfReader(input_pdf_io)
        num_pages = len(pdf_reader.pages)

        input_pdf_io.seek(0)
        reader = IncrementalPdfFileWriter(input_pdf_io)
        sig_width = 200
        sig_height = 50

        for i, coord in enumerate(coordinates):
            page = int(coord.get("page", 1)) - 1
            x = float(coord.get("x", 0))
            y = float(coord.get("y", 0))
            if page < 0 or page >= num_pages:
                frappe.throw(f"Page number {page + 1} is out of range.")
            box = (x, y, x + sig_width, y + sig_height)
            field_name = f"Signature_Page_{page+1}_{i+1}"

            sig_spec = SigFieldSpec(sig_field_name=field_name, box=box, on_page=page)
            append_signature_field(reader, sig_spec)

            signature_meta = PdfSignatureMetadata(
                field_name=field_name,
                reason=f"Digitally signed on {doctype}",
                location=digi.sign_address or "India"
            )
            signer_obj = PdfSigner(
                signature_meta,
                signer=signer,
                stamp_style=QRStampStyle(stamp_text="For: %(signer)s\nTime: %(ts)s")
            )

            output = BytesIO()
            signer_obj.sign_pdf(reader, output=output,appearance_text_params={'url': digi.url})
            output.seek(0)
            reader = IncrementalPdfFileWriter(output)

        final_output = output.getvalue()

        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"{sales_invoice.name}-signed.pdf",
            "attached_to_doctype": doctype,
            "attached_to_name": sales_invoice.name,
            "is_private": 1,
            "content": final_output,
            "decode": False,
        })
        file_doc.insert(ignore_permissions=True)

        return "success"

    except ValidationError:
        raise
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{doctype} Digital Sign Error")
        #frappe.throw(f"Failed to sign PDF: {str(e)}")
        frappe.msgprint("Error log created.")
        frappe.throw("An unexpected error occurred while processing the digital signature or you have enter wrong password in setting or PFX file invalid And Error log has been created.")

