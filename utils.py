def filtrar_produtos(produtos, categoria=None, marca=None, preco_min=None, preco_max=None):
    import unicodedata
    def normalize(text):
        return ''.join(
            c for c in unicodedata.normalize('NFD', text.lower())
            if unicodedata.category(c) != 'Mn'
        ).strip() if isinstance(text, str) else text

    resultado = []
    for p in produtos:
        if categoria and normalize(p["categoria"]) != normalize(categoria):
            continue
        if marca and normalize(p["marca"]) != normalize(marca):
            continue
        if preco_min and p["preco"] < preco_min:
            continue
        if preco_max and p["preco"] > preco_max:
            continue
        resultado.append(p)
    return resultado

def formatar_lista(produtos):
    if not produtos:
        return "Não encontrei nenhum produto com essas características."
    resposta = "Aqui estão os produtos encontrados:\n"
    for p in produtos:
        resposta += f"- {p['nome']} ({p['marca']}) - R${p['preco']}: {p['descricao']}\n"
    return resposta.strip()
