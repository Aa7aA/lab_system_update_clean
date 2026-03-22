from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"

LAB_BRANDING = {
    "logo_path": ASSETS_DIR / "lab_logo.png",
    "footer_qr_path": ASSETS_DIR / "footer_qr.png",

    "lab_name_ar": "مختبر الشفق الطبي",
    "lab_name_en": "AL-SHAFAQ LAB",

    "pdf_header_en_line1": "AL-SHAFAQ",
    "pdf_header_en_line2": "Medical Laboratory",

    "pdf_header_ar_line1": "مختبر",
    "pdf_header_ar_line2": "الشفق الطبي",
    "pdf_header_ar_line3": "للتحليلات المرضية و الهورمونات",
}