import qrcode

BASE_URL = "http://192.168.18.18:5000"

TOKENS = [
    "dev-catan-box-001",
    "dev-azul-box-001",
    "dev-terraform-box-001",
    "dev-ticket-box-001",
    "dev-risk-box-uncatalogued-001",
]

for token in TOKENS:
    url = f"{BASE_URL}/scan/{token}"
    img = qrcode.make(url)
    output_path = f"generated_qr/{token}.png"
    img.save(output_path)
    print(f"{output_path} -> {url}")
