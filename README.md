# ERPNext Digital Signature Integration

This app allows you to **digitally sign Sales Order, Sales Invoices, Purchase Order, and Purchase Invoice** in ERPNext using a visible signature via a PFX certificate. It supports selecting the **exact signature location** on a previewed PDF and then signing and attaching the signed document to the respective Sales Order, Sales Invoices, Purchase Order, and Purchase Invoice.

---

## 🔧 Features

- Digitally sign submitted Sales Invoices using your `.pfx` certificate
- Choose the exact signature position by clicking on a PDF preview
- Automatically attaches the signed PDF to the respective Sales Order, Sales Invoices, Purchase Order, and Purchase Invoice.
- Supports visible signatures on any page
- Secure password input for PFX files
- Intended usage PFX: Sign transaction, Sign document, Client Authentication, 1.3.6.1.4.1.311.10.3.12, 1.3.6.1.4.1.311.20.2.2, Acrobat Authentic Documents.

✅ Version Compatibility

| ERPNext Version | Frappe Version | Compatibility      |
| --------------- | -------------- | ------------------ |
| v14.x           | v14.x          | ✅ Fully Compatible |
| v15.x           | v15.x          | ✅ Fully Compatible |

---

## ⚙️ Setup Instructions

### 1. Install the App

```bash
cd /path/to/frappe-bench/
bench get-app https://github.com/IBSLPUNE/Digital-Signer.git
bench --site your-site-name install-app digital_signer
pip install "pyHanko[opentype]>=0.18.0" cryptography>=41.0.0 pypdf>=5.4.0 PyPDF2>=2.1.1
```
---
🔧 Document Sign Setting Configuration
To use digital signing, you must first configure the Document Sign Setting in ERPNext.

➕ Steps:
1. Go to Document Sign Setting (search in the awesome bar).

2. Fill in the fields as described below:

| Field              | Description                                                                                           |
| ------------------ | ----------------------------------------------------------------------------------------------------- |
| ✅ **PFX File Use** | Enable this if you're using a `.pfx` file for signing                                                 |
| **PFX File**       | Upload your `.pfx` certificate file (stored in `private/files/`)                                      |
| **DSC Password**   | The password for your `.pfx` file                                                                     |
| **Sign Address**   | Your signing location (e.g., `Pune Maharashtra, India`)                                               |
| **URL**            | The server URL that signs the PDF (e.g., `https://test.frappe.cloud/app`)                         |
| **Location**       | Coordinates for the visible signature in format: `(x1, y1, x2, y2)`<br>Example: `(345, 50, 545, 100)` |

PFX File Use: ✅
PFX File: file.pfx
DSC Password: "Your PFX password"
Sign Address: Pune Maharashtra, India
URL: "your site url"
Location: (345, 50, 545, 100)

![image](https://github.com/user-attachments/assets/397ba246-aa78-4499-946d-15f94c146748)




https://github.com/user-attachments/assets/c8fd4e06-e27c-4cba-8748-8ecb65207cfa





