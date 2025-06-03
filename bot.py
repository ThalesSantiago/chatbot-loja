import json
import os
import re
import unicodedata
import customtkinter as ctk
from tkinter import END

def normalize(text):
    return ''.join(
        c for c in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(c) != "Mn"
    ).strip() if isinstance(text, str) else text

def filtrar_produtos(produtos, categoria=None, marca=None, preco_min=None, preco_max=None, nome_parcial=None):
    resultado = []
    nome_parcial_norm = normalize(nome_parcial) if nome_parcial else None
    for p in produtos:
        p_categoria_norm = normalize(p.get("categoria"))
        p_marca_norm = normalize(p.get("marca"))
        p_nome_norm = normalize(p.get("nome"))
        categoria_norm = normalize(categoria)
        marca_norm = normalize(marca)

        if categoria and p_categoria_norm != categoria_norm:
            continue
        if marca and p_marca_norm != marca_norm:
            continue
        if preco_min and p.get("preco", 0) < preco_min:
            continue
        if preco_max and p.get("preco", 0) > preco_max:
            continue
        
        if nome_parcial_norm and nome_parcial_norm not in p_nome_norm:
             
             if not all(word in p_nome_norm for word in nome_parcial_norm.split()):
                 continue
        resultado.append(p)
    return resultado

def formatar_lista(produtos):
    if not produtos:
        return "Não encontrei nenhum produto com essas características."
    resposta = "Encontrei estes produtos:\n"
    for p in produtos:
        nome = p.get("nome", "Nome Indisponível")
        marca = p.get("marca", "Marca Indisponível")
        preco = p.get("preco", 0)
        descricao = p.get("descricao", "Sem descrição.")
        resposta += f"- {nome} ({marca}) - R${preco:.2f}. {descricao}\n" 
    return resposta.strip()

def extrair_preco(texto):
    texto_limpo = texto.replace(".", "").replace(",", "")
    faixa = re.findall(r"\b(\d{3,5})\b", texto_limpo)
    faixa_int = [int(f) for f in faixa]
    if "até" in texto or "no máximo" in texto or "abaixo de" in texto:
        return (None, faixa_int[0]) if faixa_int else (None, None)
    elif "acima de" in texto or "mais de" in texto or "partir de" in texto:
        return (faixa_int[0], None) if faixa_int else (None, None)
    elif "entre" in texto and len(faixa_int) >= 2:
        faixa_int.sort()
        return (faixa_int[0], faixa_int[1])
    return (None, None)

def extrair_categoria(texto):
    categorias = {
        "celular": ["celular", "smartphone", "telefone"],
        "notebook": ["notebook", "laptop"],
        "monitor": ["monitor", "tela"],
        "fone": ["fone", "fones", "headphone", "fone de ouvido", "headset"]
       
    }
    texto_norm = normalize(texto)
    for cat, termos in categorias.items():
        for termo in termos:
            if normalize(termo) in texto_norm:
                return cat
    return None

def extrair_marca(texto, marcas):
    texto_norm = normalize(texto)
    for marca in marcas:
        if normalize(marca) in texto_norm:
            return marca
    return None

def extrair_produto_mencionado(texto, produtos):
    """Tenta identificar um produto específico mencionado no texto."""
    texto_norm = normalize(texto)
    produto_encontrado = None
    maior_match = 0 
    for p in produtos:
        nome_produto_norm = normalize(p.get("nome", ""))

        if nome_produto_norm in texto_norm:
            if len(nome_produto_norm) > maior_match:
                produto_encontrado = p
                maior_match = len(nome_produto_norm)
        else:
            
            palavras_nome = nome_produto_norm.split()
            if len(palavras_nome) > 1 and all(palavra in texto_norm for palavra in palavras_nome):
                 if len(nome_produto_norm) > maior_match:
                    produto_encontrado = p
                    maior_match = len(nome_produto_norm)

    return produto_encontrado


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
produtos_path = os.path.join(BASE_DIR, "produtos.json")
marcas_path = os.path.join(BASE_DIR, "marcas.json")

try:
    with open(produtos_path, "r", encoding="utf-8") as f:
        produtos = json.load(f)
except FileNotFoundError:
    print(f"Erro: Arquivo produtos.json não encontrado em {produtos_path}")
    produtos = []
except json.JSONDecodeError:
    print(f"Erro: Falha ao decodificar produtos.json")
    produtos = []

try:
    with open(marcas_path, "r", encoding="utf-8") as f:
        marcas = json.load(f)
except FileNotFoundError:
    print(f"Erro: Arquivo marcas.json não encontrado em {marcas_path}")
    marcas = []
except json.JSONDecodeError:
    print(f"Erro: Falha ao decodificar marcas.json")
    marcas = []


class AssistenteGUI(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color="#282c34")
        self.title("AssistenteBot - Loja de Eletrônicos")
        self.geometry("600x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

       
        self.produto_contexto = None 

        self.title_label = ctk.CTkLabel(self, text="🤖 AssistenteBot", font=ctk.CTkFont(size=20, weight="bold"), text_color="#61afef")
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        self.chat_history = ctk.CTkTextbox(
            self, state="disabled", font=ctk.CTkFont(size=13),
            fg_color="#21252b", text_color="#abb2bf", border_width=0, wrap="word"
        )
        self.chat_history.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        self.chat_history.tag_config("user", foreground="#98c379")
        self.chat_history.tag_config("bot", foreground="#abb2bf")
        self.chat_history.tag_config("bot_bold", foreground="#61afef")
        self.chat_history.tag_config("link", foreground="#56b6c2", underline=True)
        self.chat_history.tag_bind("link", "<Enter>", lambda event: self.chat_history.configure(cursor="hand2"))
        self.chat_history.tag_bind("link", "<Leave>", lambda event: self.chat_history.configure(cursor=""))
        self.chat_history.tag_bind("comprar_action", "<Button-1>", self.iniciar_fluxo_compra_guiado)

        self.entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.entry_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.entry_frame.grid_columnconfigure(0, weight=1)

        self.user_input = ctk.CTkEntry(
            self.entry_frame, placeholder_text="Digite sua mensagem aqui...",
            font=ctk.CTkFont(size=13), fg_color="#2c313a", text_color="#abb2bf", border_width=0
        )
        self.user_input.grid(row=0, column=0, padx=(0, 10), sticky="ew", ipady=5)
        self.user_input.bind("<Return>", self.send_message)

        self.send_button = ctk.CTkButton(
            self.entry_frame, text="Enviar", command=self.send_message,
            font=ctk.CTkFont(size=13, weight="bold"), fg_color="#61afef",
            text_color="#282c34", hover_color="#528baf"
        )
        self.send_button.grid(row=0, column=1, sticky="e")

        self.add_message("AssistenteBot", "Olá! 👋 Posso te ajudar a encontrar o produto eletrônico ideal. O que você está buscando hoje?", tag="bot_bold")

    def fade_in_message(self, sender, message, tag="bot", link_action=None, steps=10, delay=20):
        """
        Anima a mensagem aparecendo com efeito de fade-in (mudando a cor do texto) apenas na mensagem recém inserida.
        """
        import time

        
        if tag == "user":
            start_color = "#282c34"
            end_color = "#98c379"
        elif tag == "bot_bold":
            start_color = "#282c34"
            end_color = "#61afef"
        else:
            start_color = "#282c34"
            end_color = "#abb2bf"

        def interp_color(c1, c2, t):
            c1 = [int(c1[i:i+2], 16) for i in (1, 3, 5)]
            c2 = [int(c2[i:i+2], 16) for i in (1, 3, 5)]
            return "#%02x%02x%02x" % tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

        self.chat_history.configure(state="normal")
        
        idx_start = self.chat_history.index(END + "-1c")
        if sender == "AssistenteBot":
            self.chat_history.insert(END, "🤖 Assistente: ", ("bot_bold",))
            idx_start = self.chat_history.index(END + "-1c")
            self.chat_history.insert(END, f"{message}\n\n", (tag,))
        else:
            self.chat_history.insert(END, "👤 Você: ", ("user",))
            idx_start = self.chat_history.index(END + "-1c")
            self.chat_history.insert(END, f"{message}\n\n", ("user",))
        idx_end = self.chat_history.index(END + "-1c")
        self.chat_history.configure(state="disabled")
        self.chat_history.see(END)

        
        if link_action == "comprar" and self.produto_contexto:
            self.chat_history.configure(state="normal")
            self.chat_history.tag_add("comprar_action", idx_start, idx_end)
            self.chat_history.tag_add("link", idx_start, idx_end)
            self.chat_history.configure(state="disabled")

        
        for i in range(steps):
            t = (i + 1) / steps
            color = interp_color(start_color, end_color, t)
            self.chat_history.tag_config(tag + "_fade", foreground=color)
            self.chat_history.configure(state="normal")
            self.chat_history.tag_add(tag + "_fade", idx_start, idx_end)
            self.chat_history.configure(state="disabled")
            self.chat_history.update()
            self.after(delay)
        
        self.chat_history.tag_config(tag + "_fade", foreground=end_color)
        self.chat_history.configure(state="normal")
        self.chat_history.tag_remove(tag + "_fade", idx_start, idx_end)
        self.chat_history.configure(state="disabled")

    def add_message(self, sender, message, tag="bot", link_action=None):
        self.fade_in_message(sender, message, tag=tag, link_action=link_action)

    def iniciar_fluxo_compra_guiado(self, event=None):
        """Inicia o fluxo guiado quando o usuário clica na mensagem de compra."""
        import random  
        if self.produto_contexto:
            nome_produto = self.produto_contexto.get("nome", "este produto")
            resposta_guia = (
                f"Ótima escolha o {nome_produto}! Para finalizar a compra:\n"
                f"1. Dirija-se ao setor de {self.produto_contexto.get('categoria', 'eletrônicos').capitalize()} (Corredor {random.choice([3, 5, 7])}).\n"
                f"2. Apresente este produto a um de nossos vendedores.\n"
                f"3. Finalize o pagamento no caixa principal.\n"
                f"Posso ajudar com mais alguma coisa?"
            )
            self.add_message("AssistenteBot", resposta_guia, tag="bot_bold")
            self.produto_contexto = None 
        else:
            
            self.add_message("AssistenteBot", "Para qual produto você gostaria de iniciar a compra?", tag="bot")

    def responder(self, entrada):
        cat = extrair_categoria(entrada)
        marca = extrair_marca(entrada, marcas)
        preco_min, preco_max = extrair_preco(entrada)
        produto_mencionado = extrair_produto_mencionado(entrada, produtos)

        
        if produto_mencionado:
            self.produto_contexto = produto_mencionado
        elif cat or marca:
             self.produto_contexto = None

        cumprimentos = ["oi", "olá", "ola", "e aí", "opa"]
        educados = [
            ("bom dia", "Bom dia! 😊"),
            ("boa tarde", "Boa tarde! 😊"),
            ("boa noite", "Boa noite! 😊")
        ]
        pedir_ajuda = ["ajuda", "atendente", "humano", "falar com atendente", "quero falar com atendente"]
        indefinicoes = ["não sei", "sei não", "nao sei", "não", "sei", "tanto faz", "qualquer um"]
        intencao_compra = ["comprar", "levar", "quero esse", "vou querer", "finalizar", "pagar"]

        entrada_limpa = normalize(entrada)

        
        for termo, saudacao in educados:
            if termo in entrada_limpa:
                
                resposta_padrao = self._resposta_padrao(entrada_limpa, cat, marca, preco_min, preco_max, produto_mencionado)
                if resposta_padrao:
                    return f"{saudacao} {resposta_padrao}"
                else:
                    return saudacao

        
        if any(normalize(c) == entrada_limpa for c in cumprimentos):
            return "Olá! Como posso te ajudar hoje? Buscando celular, notebook, monitor, fone ou alguma marca específica?"

        
        if any(normalize(i) in entrada_limpa for i in intencao_compra):
            if self.produto_contexto:
                return f"Excelente! Para comprar o {self.produto_contexto.get('nome')}, clique aqui para ver o passo a passo na loja."
            else:
                return "Qual produto você gostaria de comprar? Me diga o nome ou a marca."

        
        if any(p in entrada_limpa for p in [
            "parcel", "cartao", "cartão", "credito", "crédito", "vezes", "dividir", "parcela", "parcelas", "dividido", "divido"
        ]):
            produto_parcelar = produto_mencionado if produto_mencionado else self.produto_contexto
            preco_produto = produto_parcelar.get("preco", 0) if produto_parcelar else 0
            nome_produto = produto_parcelar.get("nome", "este produto") if produto_parcelar else "um produto"

            match = re.search(r"(\d{1,2})\s*(x|vezes|parcelas|dividir|dividido|divido)", entrada_limpa)
            n_parcelas = int(match.group(1)) if match else 10

            if preco_produto > 0:
                if n_parcelas > 10:
                    return f"Nosso limite é 10x sem juros no cartão. Para {nome_produto}, ficaria 10x de R${preco_produto/10:.2f}."
                if n_parcelas <= 0: n_parcelas = 1
                valor_parcela = preco_produto / n_parcelas
                if valor_parcela < 100 and n_parcelas > 1:
                    max_parcelas_possivel = int(preco_produto // 100)
                    if max_parcelas_possivel > 10: max_parcelas_possivel = 10
                    if max_parcelas_possivel >= 2:
                         valor_max_parcelas = preco_produto / max_parcelas_possivel
                         return f"A parcela mínima é R$100. Em {n_parcelas}x ficaria abaixo. Que tal {max_parcelas_possivel}x de R${valor_max_parcelas:.2f} no cartão para o {nome_produto}?"
                    else:
                         return f"A parcela mínima é R$100. Para o {nome_produto} (R${preco_produto:.2f}), não é possível parcelar mantendo o mínimo."
                return f"Sim! O {nome_produto} fica {n_parcelas}x de R${valor_parcela:.2f} sem juros no cartão."
            else:
                return (
                    "Aceitamos cartão e parcelamos em até 10x sem juros (parcela mínima R$100). ✨\n"
                    "Qual produto você gostaria de simular?"
                )

       
        if any(p in entrada_limpa for p in ["horario", "funcionamento", "abre", "fecha", "hora", "expediente"]):
            return "Nossa loja física funciona de Segunda a Sábado, das 9h às 18h. ⏰"
        if any(p in entrada_limpa for p in ["endereco", "endereço", "local", "onde fica", "localizacao", "localização", "como chegar"]):
            return "Estamos na Rua Exemplo Fictício, 123 - Centro. Quer o link do mapa? 🗺️"
        if any(p in entrada_limpa for p in ["garantia", "garantias"]):
            return "Todos os produtos têm garantia de fábrica (mínimo 12 meses). Alguns possuem garantia estendida! 👍"
        if any(p in entrada_limpa for p in ["troca", "devolucao", "devolução", "politica", "política"]):
            return "Você pode trocar ou devolver produtos em até 7 dias (sem uso, na embalagem original), conforme o CDC. 😉"

        
        if any(normalize(p) in entrada_limpa for p in pedir_ajuda):
            return "Ok! Um momento, por favor. Vou te transferir para um de nossos especialistas. 🧑‍💼"

        
        if any(normalize(p) in entrada_limpa for p in indefinicoes):
            return (
                "Tudo bem! Que tal me dizer o que você mais precisa? Ex: \"celular bom para fotos\", \"notebook leve para estudar\", \"fone com cancelamento de ruído\". 🤔"
            )

        
        if re.search(r"\bmais\s+barato(s)?\b", entrada_limpa):
            if not cat:
                if "celular" in entrada_limpa or "smartphone" in entrada_limpa: cat = "celular"
                elif "notebook" in entrada_limpa or "laptop" in entrada_limpa: cat = "notebook"
                elif "monitor" in entrada_limpa: cat = "monitor"
                elif "fone" in entrada_limpa: cat = "fone"
            produtos_filtrados = filtrar_produtos(produtos, categoria=cat, marca=marca)
            if produtos_filtrados:
                mais_baratos = sorted(produtos_filtrados, key=lambda p: p.get("preco", float("inf")))[:1]
                self.produto_contexto = mais_baratos[0]
                return formatar_lista(mais_baratos)
            else: return "Não encontrei produtos com essas características para comparar."

        if re.search(r"\bmais\s+caro(s)?\b", entrada_limpa):
            if not cat:
                if "celular" in entrada_limpa or "smartphone" in entrada_limpa: cat = "celular"
                elif "notebook" in entrada_limpa or "laptop" in entrada_limpa: cat = "notebook"
                elif "monitor" in entrada_limpa: cat = "monitor"
                elif "fone" in entrada_limpa: cat = "fone"
            produtos_filtrados = filtrar_produtos(produtos, categoria=cat, marca=marca)
            if produtos_filtrados:
                mais_caros = sorted(produtos_filtrados, key=lambda p: p.get("preco", 0), reverse=True)[:1]
                self.produto_contexto = mais_caros[0]
                return formatar_lista(mais_caros)
            else: return "Não encontrei produtos com essas características para comparar."

        nome_filtro = produto_mencionado.get("nome") if produto_mencionado else None
        resultados = filtrar_produtos(produtos, categoria=cat, marca=marca, preco_min=preco_min, preco_max=preco_max, nome_parcial=nome_filtro)

        if cat:
             resultados = [p for p in resultados if normalize(p.get("categoria", "")) == normalize(cat)]

        if resultados:
            if len(resultados) == 1:
                self.produto_contexto = resultados[0]
            else:
                self.produto_contexto = None
            return formatar_lista(resultados)
        else:
            return (
                "Hum... não encontrei exatamente isso ou não entendi bem. 😕\n"
                "Pode tentar de novo? Ex: \"celular Samsung até 2000\", \"notebook Dell\", \"monitor LG\".\n"
                "Ou digite \"ajuda\" para falar com um especialista."
            )

    def _resposta_padrao(self, entrada_limpa, cat, marca, preco_min, preco_max, produto_mencionado):
       
        intencao_compra = ["comprar", "levar", "quero esse", "vou querer", "finalizar", "pagar"]
        if any(normalize(i) in entrada_limpa for i in intencao_compra):
            if self.produto_contexto:
                return f"Para comprar o {self.produto_contexto.get('nome')}, clique aqui para ver o passo a passo na loja."
            else:
                return "Qual produto você gostaria de comprar? Me diga o nome ou a marca."
        
        if any(p in entrada_limpa for p in [
            "parcel", "cartao", "cartão", "credito", "crédito", "vezes", "dividir", "parcela", "parcelas", "dividido", "divido"
        ]):
            produto_parcelar = produto_mencionado if produto_mencionado else self.produto_contexto
            preco_produto = produto_parcelar.get("preco", 0) if produto_parcelar else 0
            nome_produto = produto_parcelar.get("nome", "este produto") if produto_parcelar else "um produto"
            match = re.search(r"(\d{1,2})\s*(x|vezes|parcelas|dividir|dividido|divido)", entrada_limpa)
            n_parcelas = int(match.group(1)) if match else 10
            if preco_produto > 0:
                if n_parcelas > 10:
                    return f"Nosso limite é 10x sem juros no cartão. Para {nome_produto}, ficaria 10x de R${preco_produto/10:.2f}."
                if n_parcelas <= 0: n_parcelas = 1
                valor_parcela = preco_produto / n_parcelas
                if valor_parcela < 100 and n_parcelas > 1:
                    max_parcelas_possivel = int(preco_produto // 100)
                    if max_parcelas_possivel > 10: max_parcelas_possivel = 10
                    if max_parcelas_possivel >= 2:
                         valor_max_parcelas = preco_produto / max_parcelas_possivel
                         return f"A parcela mínima é R$100. Em {n_parcelas}x ficaria abaixo. Que tal {max_parcelas_possivel}x de R${valor_max_parcelas:.2f} no cartão para o {nome_produto}?"
                    else:
                         return f"A parcela mínima é R$100. Para o {nome_produto} (R${preco_produto:.2f}), não é possível parcelar mantendo o mínimo."
                return f"O {nome_produto} fica {n_parcelas}x de R${valor_parcela:.2f} sem juros no cartão."
            else:
                return (
                    "Aceitamos cartão e parcelamos em até 10x sem juros (parcela mínima R$100). ✨\n"
                    "Qual produto você gostaria de simular?"
                )
        if any(p in entrada_limpa for p in ["horario", "funcionamento", "abre", "fecha", "hora", "expediente"]):
            return "Nossa loja física funciona de Segunda a Sábado, das 9h às 18h. ⏰"
        if any(p in entrada_limpa for p in ["endereco", "endereço", "local", "onde fica", "localizacao", "localização", "como chegar"]):
            return "Estamos na Rua Exemplo Fictício, 123 - Centro. Quer o link do mapa? 🗺️"
        if any(p in entrada_limpa for p in ["garantia", "garantias"]):
            return "Todos os produtos têm garantia de fábrica (mínimo 12 meses). Alguns possuem garantia estendida! 👍"
        if any(p in entrada_limpa for p in ["troca", "devolucao", "devolução", "politica", "política"]):
            return "Você pode trocar ou devolver produtos em até 7 dias (sem uso, na embalagem original), conforme o CDC. 😉"
        
        pedir_ajuda = ["ajuda", "atendente", "humano", "falar com atendente", "quero falar com atendente"]
        if any(normalize(p) in entrada_limpa for p in pedir_ajuda):
            return "Ok! Um momento, por favor. Vou te transferir para um de nossos especialistas. 🧑‍💼"
        
        indefinicoes = ["não sei", "sei não", "nao sei", "não", "sei", "tanto faz", "qualquer um"]
        if any(normalize(p) in entrada_limpa for p in indefinicoes):
            return (
                "Tudo bem! Que tal me dizer o que você mais precisa? Ex: \"celular bom para fotos\", \"notebook leve para estudar\", \"fone com cancelamento de ruído\". 🤔"
            )
        
        if re.search(r"\bmais\s+barato(s)?\b", entrada_limpa):
            if not cat:
                if "celular" in entrada_limpa or "smartphone" in entrada_limpa: cat = "celular"
                elif "notebook" in entrada_limpa or "laptop" in entrada_limpa: cat = "notebook"
                elif "monitor" in entrada_limpa: cat = "monitor"
                elif "fone" in entrada_limpa: cat = "fone"
            produtos_filtrados = filtrar_produtos(produtos, categoria=cat, marca=marca)
            if produtos_filtrados:
                mais_baratos = sorted(produtos_filtrados, key=lambda p: p.get("preco", float("inf")))[:1]
                self.produto_contexto = mais_baratos[0]
                return formatar_lista(mais_baratos)
            else: return "Não encontrei produtos com essas características para comparar."
        if re.search(r"\bmais\s+caro(s)?\b", entrada_limpa):
            if not cat:
                if "celular" in entrada_limpa or "smartphone" in entrada_limpa: cat = "celular"
                elif "notebook" in entrada_limpa or "laptop" in entrada_limpa: cat = "notebook"
                elif "monitor" in entrada_limpa: cat = "monitor"
                elif "fone" in entrada_limpa: cat = "fone"
            produtos_filtrados = filtrar_produtos(produtos, categoria=cat, marca=marca)
            if produtos_filtrados:
                mais_caros = sorted(produtos_filtrados, key=lambda p: p.get("preco", 0), reverse=True)[:1]
                self.produto_contexto = mais_caros[0]
                return formatar_lista(mais_caros)
            else: return "Não encontrei produtos com essas características para comparar."
        
        nome_filtro = produto_mencionado.get("nome") if produto_mencionado else None
        resultados = filtrar_produtos(produtos, categoria=cat, marca=marca, preco_min=preco_min, preco_max=preco_max, nome_parcial=nome_filtro)
        if cat:
             resultados = [p for p in resultados if normalize(p.get("categoria", "")) == normalize(cat)]
        if resultados:
            if len(resultados) == 1:
                self.produto_contexto = resultados[0]
            else:
                self.produto_contexto = None
            return formatar_lista(resultados)
        else:
            return (
                "Hum... não encontrei exatamente isso ou não entendi bem. 😕\n"
                "Pode tentar de novo? Ex: \"celular Samsung até 2000\", \"notebook Dell\", \"monitor LG\".\n"
                "Ou digite \"ajuda\" para falar com um especialista."
            )

    def send_message(self, event=None):
        user_msg = self.user_input.get()
        if not user_msg.strip():
            return
        self.add_message("Você", user_msg, tag="user")
        self.user_input.delete(0, END)

        despedidas = ["tchau", "sair", "encerrar", "xau", "adeus", "até mais", "falou"]
        if any(p in user_msg.lower().strip() for p in despedidas):
            self.add_message("AssistenteBot", "Até logo! Volte sempre. 😊", tag="bot_bold")
            self.after(1500, self.destroy)
            return

        resposta = self.responder(user_msg)

        
        tag_resposta = "bot"
        acao_link = None
        if resposta.startswith("Ok!") or resposta.startswith("Sim!") or resposta.startswith("Ótima escolha") or resposta.startswith("Nossa loja") or resposta.startswith("Estamos") or resposta.startswith("Todos os produtos") or resposta.startswith("Você pode"):
            tag_resposta = "bot_bold"
        if resposta.startswith("Excelente!"): 
            tag_resposta = "bot_bold"
            acao_link = "comprar"

        self.add_message("AssistenteBot", resposta, tag=tag_resposta, link_action=acao_link)


if __name__ == "__main__":
    app = AssistenteGUI()
    app.mainloop()

