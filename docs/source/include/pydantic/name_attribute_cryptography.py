from cryptography import x509
from cryptography.x509.oid import NameOID

x509.NameAttribute(oid=NameOID.COMMON_NAME, value="example.com")
