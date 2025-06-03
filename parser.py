import re

def extrair_preco(texto):
    faixa = re.findall(r"(\d{3,5})", texto.replace('.', '').replace(',', ''))
    if "até" in texto or "no máximo" in texto:
        return (None, int(faixa[0])) if faixa else (None, None)
    elif "acima de" in texto or "mais de" in texto:
        return (int(faixa[0]), None) if faixa else (None, None)
    elif "entre" in texto and len(faixa) >= 2:
        return (int(faixa[0]), int(faixa[1]))
    return (None, None)

def extrair_categoria(texto):
    categorias = {
        "celular": ["celular", "smartphone", "telefone"],
        "notebook": ["notebook", "laptop"],
        "monitor": ["monitor", "tela"],
        "fone": ["fone", "fones", "headphone", "fone de ouvido"]
    }
    for cat, termos in categorias.items():
        for termo in termos:
            if termo in texto:
                return cat
    return None

def extrair_marca(texto, marcas):
    texto = texto.lower()
    for marca in marcas:
        if marca.lower() in texto:
            return marca
    return None
