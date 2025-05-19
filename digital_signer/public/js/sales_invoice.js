
frappe.ui.form.on("Sales Invoice", {
    refresh: function(frm) {
        if (frm.doc.docstatus == 1) {
            frm.add_custom_button("Sign & Attach PDF", function() {

                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Print Format",
                        filters: {
                            doc_type: "Sales Invoice",
                            disabled : 0
                        },
                        fields: ["name"]
                    },
                    callback: function(res) {
                        if (res.message) {
                            let print_formats = res.message.map(f => f.name);

                            let d = new frappe.ui.Dialog({
                                title: 'Choose Print Format',
                                fields: [
                                    {
                                        label: 'Select Print Format',
                                        fieldname: 'print_format',
                                        fieldtype: 'Select',
                                        options: print_formats,
                                        reqd: 1
                                    },
                                    {
                                        fieldname: 'password',
                                        fieldtype: 'Password',
                                        label: 'Enter PFX Password',
                                        reqd: 1
                                    },
                                    {
                                        fieldname: 'multiple_page_sign',
                                        fieldtype: 'Check',
                                        label: 'Sign All Pages (Multiple Pages)',
                                        depends_on: 'eval: !doc.page_range_enable'
                                    },
                                    {
                                        fieldname: 'page_range_enable',
                                        fieldtype: 'Check',
                                        label: 'Sign Specific Page Range',
                                        depends_on: 'eval: !doc.multiple_page_sign'
                                    },
                                    {
                                        fieldname: 'page_range',
                                        fieldtype: 'Data',
                                        label: 'Page Range (e.g., 1,3-5)',
                                        depends_on: 'eval: doc.page_range_enable'
                                    }
                                ],
                                primary_action_label: 'Sign & Attach',
                                primary_action(values) {
                                    d.hide();
                                    frappe.call({
                                        method: "digital_signer.api.sign_sales_invoice_pdf",
                                        args: {
                                            doctype: frm.doctype,
                                            sales_invoice_name: frm.doc.name,
                                            print_format_name: values.print_format,
                                            entered_password: values.password,
                                            multiple_page: values.multiple_page_sign ? 1 : 0,
                                            page_range: values.page_range || ""
                                        },
                                        callback: function(r) {
                                            if (!r.exc) {
                                                frappe.msgprint("Signed PDF attached successfully!");
                                                frm.reload_doc();
                                            }
                                        }
                                    });
                                }
                            });

                            d.show();
                        }
                    }
                });
            },"Sign");
            frm.add_custom_button("Sign with Preview PDF", function() {

                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Print Format",
                        filters: {
                            doc_type: "Sales Invoice",
                            disabled: 0
                        },
                        fields: ["name"]
                    },
                    callback: function(res) {
                        if (res.message) {
                            let print_formats = res.message.map(f => f.name);
                            let signature_data = []; // array to hold multiple signature locations

                            const dialog = new frappe.ui.Dialog({
                                title: 'Sign PDF',
                                fields: [
                                    {
                                        label: 'Select Print Format',
                                        fieldname: 'print_format',
                                        fieldtype: 'Select',
                                        options: print_formats,
                                        reqd: 1
                                    },
                                    {
                                        label: 'PFX Password',
                                        fieldname: 'password',
                                        fieldtype: 'Password',
                                        reqd: 1
                                    },
                                    {
                                        label: 'Preview & Select Signature Locations',
                                        fieldname: 'preview_btn',
                                        fieldtype: 'Button'
                                    }
                                ],
                                primary_action_label: 'Sign & Attach',
                                primary_action(values) {
                                    if (signature_data.length === 0) {
                                        frappe.msgprint("Please select at least one signature location.");
                                        return;
                                    }
                                    dialog.hide();
                                    frappe.call({
                                        method: "digital_signer.preview_api.sign_sales_invoice_pdf",
                                        args: {
                                            doctype: frm.doctype,
                                            sales_invoice_name: frm.doc.name,
                                            print_format_name: values.print_format,
                                            entered_password: values.password,
                                            coordinates_json: JSON.stringify(signature_data) // send locations as JSON string
                                        },
                                        callback: function(r) {
                                            if (!r.exc) {
                                                frappe.msgprint("Signed PDF attached successfully!");
                                                frm.reload_doc();
                                            }
                                        }
                                    });
                                }
                            });

                            // Preview button click: open PDF pages with canvas and allow multiple signature clicks
                            dialog.fields_dict.preview_btn.df.click = function() {
                                const print_format = dialog.get_value('print_format');
                                if (!print_format) {
                                    frappe.msgprint("Please select a print format.");
                                    return;
                                }

                                const pdf_url = `/api/method/frappe.utils.print_format.download_pdf?doctype=Sales Invoice&name=${frm.doc.name}&format=${print_format}&no_letterhead=0`;
                                const previewWindow = window.open("", "_blank");

                                previewWindow.document.write(`
                                    <html>
                                    <head>
                                        <title>Select Signature Locations</title>
                                        <style>
                                            body { font-family: Arial; margin: 0; padding: 10px; }
                                            canvas { display: block; margin-bottom: 20px; border: 1px solid #ccc; cursor: crosshair; }
                                            h3 { margin-bottom: 10px; }
                                        </style>
                                    </head>
                                    <body>
                                        <h3>Click on the location where you want the signature (multiple locations allowed)</h3>
                                        <div id="pdf-container"></div>

                                        <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.13.216/pdf.min.js"></script>
                                        <script>
                                            const url = "${pdf_url}";
                                            const container = document.getElementById("pdf-container");
                                            const scale = 1.5;

                                            pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.13.216/pdf.worker.min.js";

                                            pdfjsLib.getDocument(url).promise.then(pdf => {
                                                for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
                                                    pdf.getPage(pageNum).then(page => {
                                                        const viewport = page.getViewport({ scale: scale });
                                                        const canvas = document.createElement("canvas");
                                                        canvas.width = viewport.width;
                                                        canvas.height = viewport.height;
                                                        canvas.dataset.page = pageNum;
                                                        const context = canvas.getContext("2d");

                                                        page.render({ canvasContext: context, viewport: viewport });

                                                        canvas.addEventListener("click", function(event) {
                                                            const rect = canvas.getBoundingClientRect();

                                                            const clickX = event.clientX - rect.left;
                                                            const clickY = event.clientY - rect.top;

                                                            // convert to PDF coordinates (scale and flip Y)
                                                            const pdfX = clickX / scale;
                                                            const pdfY = (rect.height - clickY) / scale;

                                                            window.opener.postMessage({
                                                                type: "signature_location",
                                                                x: Math.round(pdfX),
                                                                y: Math.round(pdfY),
                                                                page: parseInt(canvas.dataset.page)
                                                            }, "*");

                                                            alert("Signature location captured at X: " + Math.round(pdfX) + ", Y: " + Math.round(pdfY) + ". You can select more or close this window.");
                                                        });

                                                        container.appendChild(canvas);
                                                    });
                                                }
                                            });
                                        </script>
                                    </body>
                                    </html>
                                `);
                                previewWindow.document.close();
                            };

                            // Listen for messages from popup window with clicked signature locations
                            window.addEventListener("message", function(event) {
                                if (event.data && event.data.type === "signature_location") {
                                    signature_data.push(event.data);
                                    frappe.msgprint(`Signature location added: Page ${event.data.page}, X: ${event.data.x}, Y: ${event.data.y}`);
                                }
                            });

                            dialog.show();
                        }
                    }
                });
            },"Sign");
        }
    }
});




