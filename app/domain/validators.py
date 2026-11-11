"""Validaciones de los datos del prospecto. Reglas puras del dominio."""
import re

_LETTERS = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
_FULL_NAME = re.compile(rf"[{_LETTERS}'-]+( [{_LETTERS}'-]+)+")  # nombre + apellido(s)
_FOREIGN_RESIDENT_PROVINCE = 30


def is_valid_name(name: str) -> bool:
    return bool(_FULL_NAME.fullmatch(name)) and len(name) <= 120


def is_valid_cedula(document_id: str) -> bool:
    """Cédula ecuatoriana: 10 dígitos, provincia 01-24 (o 30 para extranjeros),
    tercer dígito < 6 (persona natural) y dígito verificador módulo 10."""
    if not re.fullmatch(r"[0-9]{10}", document_id):
        return False
    province, third = int(document_id[:2]), int(document_id[2])
    if not (1 <= province <= 24 or province == _FOREIGN_RESIDENT_PROVINCE) or third >= 6:
        return False
    total = 0
    for i, digit in enumerate(document_id[:9]):
        n = int(digit) * (2 if i % 2 == 0 else 1)
        total += n - 9 if n > 9 else n
    return (10 - total % 10) % 10 == int(document_id[9])
