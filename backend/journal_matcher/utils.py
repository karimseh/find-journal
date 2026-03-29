import re

def normalize_issn(raw):
    if raw is None:
        return None
    normalized_issn = raw.replace('-', '').replace(' ', '').strip().upper()
    if len(normalized_issn) != 8:
        return None
    return normalized_issn

def issn_with_hyphen(issn):
    if issn is None:
        return None
    if len(issn) != 8:
        return None
    return issn[:4] + '-' + issn[4:]

def clean_text(text):
    if text is None:
        return None
    return re.sub(r'\s+', ' ', text).strip()

def safe_float(value):
    try:
        val = str(value).replace(',', '.').strip()
        return float(val)
    except (ValueError, TypeError):
        return None
    
def safe_int(value):
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None
    