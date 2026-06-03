"""
Utilidades compartidas entre scripts.
"""

def fix_name(n):
    raw = n.encode('utf-8')
    fixes = {
        b'IV\xc3\x83\xc2\x81N CEPEDA CASTRO': 'IV\u00c1N CEPEDA CASTRO',
        b'CLAUDIA L\xc3\x83\xe2\x80\x9cPEZ': 'CLAUDIA L\u00d3PEZ',
        b'RA\xc3\x83\xc5\xa1L SANTIAGO BOTERO JARAMILLO': 'RA\u00daL SANTIAGO BOTERO JARAMILLO',
        b'\xc3\x83\xe2\x80\x9cSCAR MAURICIO LIZCANO ARANGO': '\u00d3SCAR MAURICIO LIZCANO ARANGO',
        b'MIGUEL URIBE LONDO\xc3\x83\xe2\x80\x98O': 'MIGUEL URIBE LONDO\u00d1O',
    }
    return fixes.get(raw, n)
