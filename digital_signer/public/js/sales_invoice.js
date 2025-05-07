frappe.ui.form.on("Sales Invoice", {
    refresh: function(frm) {
        if (frm.doc.docstatus == 1) {  // Only show when submitted
            frm.add_custom_button("Sign & Attach PDF", function() {

                // Get available print formats for this DocType
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Print Format",
                        filters: {
                            doc_type: "Sales Invoice"
                        },
                        fields: ["name"]
                    },
                    callback: function(res) {
                        if (res.message) {
                            let print_formats = res.message.map(f => f.name);

                            frappe.prompt([
                                {
                                    label: 'Select Print Format',
                                    fieldname: 'print_format',
                                    fieldtype: 'Select',
                                    options: print_formats,
                                    reqd: 1
                                }
                            ],
                            function(values) {
                                // Call the server-side method with selected print format
                                frappe.call({
                                    method: "digital_signer.api.sign_sales_invoice_pdf",
                                    args: {
                                        sales_invoice_name: frm.doc.name,
                                        print_format_name: values.print_format
                                    },
                                    callback: function(r) {
                                        if (!r.exc) {
                                            frappe.msgprint("Signed PDF attached successfully!");
                                            frm.reload_doc();
                                        }
                                    }
                                });
                            },
                            'Choose Print Format',
                            'Sign & Attach');
                        }
                    }
                });
            });
        }
    }
});
