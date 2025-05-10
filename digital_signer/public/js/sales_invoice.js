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
            });
        }
    }
});

