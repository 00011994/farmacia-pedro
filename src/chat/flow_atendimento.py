import re
import unicodedata
from typing import Dict, List, Optional, Tuple

from src.chat.data import DataGateway, ProdutoInfo


def _normalize(text: str) -> str:
    cleaned = text.strip().lower()
    cleaned = unicodedata.normalize("NFD", cleaned)
    cleaned = "".join(ch for ch in cleaned if unicodedata.category(ch) != "Mn")
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _extract_qty(text: str) -> Optional[int]:
    match = re.search(r"\b(\d{1,3})\b", text)
    if not match:
        return None
    try:
        value = int(match.group(1))
    except ValueError:
        return None
    return value if 1 <= value <= 999 else None


def _extract_qty_list(text: str) -> List[int]:
    values = []
    for item in re.findall(r"\b(\d{1,3})\b", text):
        try:
            value = int(item)
        except ValueError:
            continue
        if 1 <= value <= 999:
            values.append(value)
    return values


def _is_pickup(text: str) -> bool:
    msg = _normalize(text)
    return any(k in msg for k in ["retirar", "retirada", "loja", "buscar", "vou ai", "vou na loja"])


def _is_delivery(text: str) -> bool:
    msg = _normalize(text)
    return any(k in msg for k in ["entrega", "entregar", "delivery", "casa", "mandar", "envio"])


def _parse_delivery_rules(raw: str) -> List[Tuple[str, float, str]]:
    rules: List[Tuple[str, float, str]] = []
    if not raw:
        return rules
    for chunk in raw.split(";"):
        part = chunk.strip()
        if not part:
            continue
        bits = [b.strip() for b in part.split(":")]
        if len(bits) < 2:
            continue
        bairro = bits[0]
        try:
            taxa = float(bits[1])
        except ValueError:
            taxa = 0.0
        prazo = bits[2] if len(bits) > 2 else ""
        rules.append((bairro, taxa, prazo))
    return rules


def _match_delivery_rule(bairro: str, rules: List[Tuple[str, float, str]]) -> Optional[Tuple[str, float, str]]:
    bairro_norm = _normalize(bairro)
    sorted_rules = sorted(rules, key=lambda r: len(r[0]), reverse=True)
    for rule in sorted_rules:
        key_norm = _normalize(rule[0])
        if key_norm and key_norm in bairro_norm:
            return rule
    return None


class AtendimentoFlow:
    def __init__(self, settings, gateway: DataGateway) -> None:
        self.settings = settings
        self.gateway = gateway
        self.delivery_rules = _parse_delivery_rules(settings.chat_delivery_rules)

    def handle(self, state: str, data: Dict, message: str) -> Tuple[str, str, Dict]:
        msg_norm = _normalize(message)

        if msg_norm in {"sair", "encerrar", "fim"}:
            return "Encerrando atendimento. Obrigado por conversar com a gente!", "DONE", {}

        if msg_norm in {"ajuda", "menu", "comandos"}:
            return self._help(), state, data

        # Novo: estados para nome e contato
        if state == "ASK_CLIENT_NAME":
            data["nome_cliente"] = message.strip().title()
            return (f"Obrigado, {data['nome_cliente']}! Podemos te chamar nesse número se precisarmos falar sobre seu pedido? (Responda sim ou não)", "ASK_CONTACT_PERMISSION", data)

        if state == "ASK_CONTACT_PERMISSION":
            if msg_norm in {"sim", "pode", "claro", "ok", "sim pode", "sim, pode", "pode sim"}:
                data["pode_contato"] = True
            else:
                data["pode_contato"] = False
            # Log do pedido
            self._log_pedido(data)
            return ("Seu pedido foi registrado! Assim que o entregador sair para entrega, avisaremos por aqui. Precisa de mais alguma coisa?", "DONE", data)

        if state == "START":
            return self._handle_start(data, message)

        if state == "ASK_PRODUCT_CHOICE":
            return self._handle_choice(data, message)

        if state == "ASK_VARIANT":
            return self._handle_variant(data, message)

        if state == "ASK_QTY":
            return self._handle_qty(data, message)

        if state == "ASK_CART_QTY":
            return self._handle_cart_qty(data, message)

        if state == "OUT_OF_STOCK":
            return self._handle_out_of_stock(data, message)

        if state == "ASK_FULFILLMENT":
            return self._handle_fulfillment(data, message)

        if state == "PICKUP_CONFIRM":
            return self._handle_pickup_confirm(data, message)

        if state == "DELIVERY_ADDRESS":
            return self._handle_delivery_address(data, message)

        if state == "DELIVERY_DETAILS":
            return self._handle_delivery_details(data, message)

        if state == "DONE":
            # Humanização e compreensão flexível
            if msg_norm in {"nao", "não", "nao quero", "não quero", "obrigado", "obrigada", "só", "so", "só isso", "so isso", "n", "no", "acho que não", "talvez depois", "por enquanto não"}:
                return "Perfeito, seu pedido está finalizado! Se precisar de mais alguma coisa, é só chamar. Tenha um ótimo dia!", "DONE", data
            if msg_norm in {"sim", "quero", "adicionar", "sim quero", "sim, quero", "sim por favor", "mais", "adicionar item", "adicionar mais"}:
                return "Claro! Me diz o próximo produto que você quer adicionar.", "START", {}
            return ("Se quiser adicionar mais algum item, é só falar o nome do produto. Se não, pode responder 'não' para finalizar o pedido! 😊", "DONE", data)

        return self._greeting(), "START", {}

    def _greeting(self) -> str:
        return (
            f"Oi! {self.settings.chat_loja_nome} ({self.settings.chat_endereco}). "
            "Me diz o produto que voce procura que eu vejo preco e disponibilidade."
        )

    def _help(self) -> str:
        return (
            "Exemplos:\n"
            "- Tem dipirona?\n"
            "- Quero amoxicilina 500mg\n"
            "- Separar dipirona e alcool gel\n"
            "- Retirar na loja\n"
            "- Entrega em casa\n"
            "- sair"
        )

    def _handle_start(self, data: Dict, message: str) -> Tuple[str, str, Dict]:
        msg_norm = _normalize(message)
        if " e " in msg_norm or "," in message:
            partes = [p.strip() for p in re.split(r"\be\b|,", msg_norm) if p.strip()]
            produtos: List[ProdutoInfo] = []
            for parte in partes:
                encontrados = self.gateway.search_products(parte, limit=1)
                if encontrados:
                    produtos.append(encontrados[0])
            if len(produtos) >= 2:
                data["carrinho"] = [self._to_dict(prod) for prod in produtos]
                nomes = [prod.nome for prod in produtos]
                lista = "\n".join(f"- {nome}" for nome in nomes)
                return (
                    "Fechado. Me confirma a quantidade de cada item (responda no formato: 2, 1, 3):\n" + lista,
                    "ASK_CART_QTY",
                    data,
                )

        matches = self.gateway.search_products(message, limit=5)
        if not matches:
            return self._greeting(), "START", {}

        if len(matches) > 1 and (" e " in msg_norm or "," in message):
            data["carrinho"] = [self._to_dict(prod) for prod in matches]
            nomes = [prod.nome for prod in matches]
            lista = "\n".join(f"- {nome}" for nome in nomes)
            return (
                "Fechado. Me confirma a quantidade de cada item (responda no formato: 2, 1, 3):\n" + lista,
                "ASK_CART_QTY",
                data,
            )

        if len(matches) > 1:
            data["opcoes"] = [self._to_dict(prod) for prod in matches]
            linhas = [f"{idx+1}) {prod.nome}" for idx, prod in enumerate(matches)]
            return (
                "Encontrei mais de um produto. Qual voce quer?\n" + "\n".join(linhas),
                "ASK_PRODUCT_CHOICE",
                data,
            )

        produto = matches[0]
        data["produto"] = self._to_dict(produto)
        variantes = self._variants_for(produto)
        if variantes:
            data["variantes"] = variantes
            return (
                f"Tenho sim. Voce quer {variantes[0]} ou {variantes[1]}?",
                "ASK_VARIANT",
                data,
            )

        return (
            f"Beleza! {produto.nome} esta R$ {produto.preco:.2f} e tem disponivel agora na {self.settings.chat_filial}. "
            "Quantas unidades voce quer?",
            "ASK_QTY",
            data,
        )

    def _handle_choice(self, data: Dict, message: str) -> Tuple[str, str, Dict]:
        opcoes = data.get("opcoes", [])
        if not opcoes:
            return self._greeting(), "START", {}

        msg_norm = _normalize(message)
        match_num = _extract_qty(msg_norm)
        escolhido = None
        if match_num:
            idx = match_num - 1
            if 0 <= idx < len(opcoes):
                escolhido = opcoes[idx]
        if not escolhido:
            for opcao in opcoes:
                if _normalize(opcao.get("nome", "")) in msg_norm:
                    escolhido = opcao
                    break
        if not escolhido:
            return ("Me diz o numero da opcao ou o nome do produto.", "ASK_PRODUCT_CHOICE", data)

        data["produto"] = escolhido
        data.pop("opcoes", None)
        produto = self._from_dict(escolhido)
        variantes = self._variants_for(produto)
        if variantes:
            data["variantes"] = variantes
            return (
                f"Tenho sim. Voce quer {variantes[0]} ou {variantes[1]}?",
                "ASK_VARIANT",
                data,
            )

        return (
            f"Beleza! {produto.nome} esta R$ {produto.preco:.2f} e tem disponivel agora na {self.settings.chat_filial}. "
            "Quantas unidades voce quer?",
            "ASK_QTY",
            data,
        )

    def _handle_variant(self, data: Dict, message: str) -> Tuple[str, str, Dict]:
        produto_raw = data.get("produto")
        if not produto_raw:
            return self._greeting(), "START", {}
        data["variante"] = message.strip()
        produto = self._from_dict(produto_raw)
        return (
            f"Fechado. {produto.nome} ({data['variante']}) esta R$ {produto.preco:.2f} e tem disponivel agora na {self.settings.chat_filial}. "
            "Quantas unidades voce quer?",
            "ASK_QTY",
            data,
        )

    def _handle_qty(self, data: Dict, message: str) -> Tuple[str, str, Dict]:
        qty = _extract_qty(message)
        if not qty:
            return "Perfeito. Me diz a quantidade (ex.: 1, 2, 3).", "ASK_QTY", data

        produto_raw = data.get("produto")
        if not produto_raw:
            return self._greeting(), "START", {}
        produto = self._from_dict(produto_raw)
        if produto.estoque <= 0:
            data["produto_out"] = produto_raw
            return (
                f"No momento, acabou aqui na {self.settings.chat_filial}. Quer que eu sugira uma alternativa ou te avise quando chegar?",
                "OUT_OF_STOCK",
                data,
            )
        if qty > produto.estoque:
            return (
                f"Aqui na {self.settings.chat_filial} eu tenho {produto.estoque} unidade(s) disponivel agora. "
                "Voce quer essa quantidade mesmo ou ajusta?",
                "ASK_QTY",
                data,
            )

        data["quantidade"] = qty
        if _is_delivery(message):
            return "Fechado. Me passa seu bairro e rua (pode ser sem numero por enquanto).", "DELIVERY_ADDRESS", data
        if _is_pickup(message):
            return "Perfeito. Em quanto tempo voce pretende retirar? (ex.: 30 min, 1h, hoje)", "PICKUP_CONFIRM", data

        return "Voce prefere reservar pra retirar na loja ou receber em casa?", "ASK_FULFILLMENT", data

    def _handle_cart_qty(self, data: Dict, message: str) -> Tuple[str, str, Dict]:
        carrinho = data.get("carrinho", [])
        if not carrinho:
            return self._greeting(), "START", {}
        quantidades = _extract_qty_list(message)
        if len(quantidades) != len(carrinho):
            return (
                "Me passa a quantidade de cada item na mesma ordem (ex.: 2, 1, 3).",
                "ASK_CART_QTY",
                data,
            )
        data["quantidades"] = quantidades
        return "Voce prefere retirar na loja ou entrega em casa?", "ASK_FULFILLMENT", data

    def _handle_out_of_stock(self, data: Dict, message: str) -> Tuple[str, str, Dict]:
        msg_norm = _normalize(message)
        produto_raw = data.get("produto_out") or data.get("produto")
        if not produto_raw:
            return self._greeting(), "START", {}
        produto = self._from_dict(produto_raw)

        if "alternativa" in msg_norm:
            alternativas = self.gateway.suggest_alternatives(produto.categoria, produto.sku, limit=2)
            if alternativas:
                linhas = [f"- {alt.nome} (R$ {alt.preco:.2f})" for alt in alternativas]
                return (
                    "Aqui vao alternativas parecidas:\n" + "\n".join(linhas) + "\nQuer alguma delas?",
                    "ASK_PRODUCT_CHOICE",
                    {"opcoes": [self._to_dict(a) for a in alternativas]},
                )
            return (
                "No momento nao tenho alternativas. Quer que eu te avise quando chegar?",
                "OUT_OF_STOCK",
                data,
            )

        if "avisar" in msg_norm or "avise" in msg_norm:
            return (
                "Combinado. Assim que chegar eu te aviso. Quer adicionar mais algum item?",
                "DONE",
                data,
            )

        return "Voce prefere uma alternativa agora ou quer que eu te avise quando chegar?", "OUT_OF_STOCK", data

    def _handle_fulfillment(self, data: Dict, message: str) -> Tuple[str, str, Dict]:
        if _is_pickup(message):
            return "Perfeito. Em quanto tempo voce pretende retirar? (ex.: 30 min, 1h, hoje)", "PICKUP_CONFIRM", data
        if _is_delivery(message):
            return "Fechado. Me passa seu bairro e rua (pode ser sem numero por enquanto).", "DELIVERY_ADDRESS", data
        return "So pra eu fechar certinho: voce prefere retirar na loja ou entrega em casa?", "ASK_FULFILLMENT", data

    def _handle_pickup_confirm(self, data: Dict, message: str) -> Tuple[str, str, Dict]:
        data["retirada_em"] = message.strip()
        produto_raw = data.get("produto")
        if produto_raw:
            produto = self._from_dict(produto_raw)
            qty = data.get("quantidade", 1)
            validade = self.settings.chat_reserva_validade
            info_validade = f" Sua reserva fica garantida ate {validade}." if validade else ""
            return (
                f"Fechado. Reservei {qty} unidade(s) de {produto.nome} para retirada {data['retirada_em']} na {self.settings.chat_loja_nome}."
                + info_validade
                + " Quer que eu te mande a localizacao e o horario de funcionamento?",
                "DONE",
                data,
            )
        return "Reserva confirmada. Quer que eu te mande a localizacao e o horario?", "DONE", data

    def _handle_delivery_address(self, data: Dict, message: str) -> Tuple[str, str, Dict]:
        data["endereco_parcial"] = message.strip()
        rule = _match_delivery_rule(message, self.delivery_rules)
        if rule:
            bairro, taxa, prazo = rule
            prazo_txt = f" (prazo: {prazo})" if prazo else ""
            data["taxa_entrega"] = taxa
            data["prazo_entrega"] = prazo
            return (
                f"Perfeito. Taxa de entrega para {bairro}: R$ {taxa:.2f}{prazo_txt}. "
                "Agora me manda: numero (ou referencia) + forma de pagamento (Pix ou cartao) + melhor horario.",
                "DELIVERY_DETAILS",
                data,
            )
        return (
            f"Perfeito. {self.settings.chat_delivery_fallback} "
            "Agora me manda: numero (ou referencia) + forma de pagamento (Pix ou cartao) + melhor horario.",
            "DELIVERY_DETAILS",
            data,
        )

    def _handle_delivery_details(self, data: Dict, message: str) -> Tuple[str, str, Dict]:
        data["entrega_detalhes"] = message.strip()
        produto_raw = data.get("produto")
        qty = data.get("quantidade", 1)
        if produto_raw:
            produto = self._from_dict(produto_raw)
            # Ao finalizar, pedir nome do cliente
            return (
                f"Beleza. Vou preparar {qty} unidade(s) de {produto.nome}. Agora, pra finalizar seu pedido, qual seu nome?", "ASK_CLIENT_NAME", data
            )
        return (
            "Beleza. Agora, pra finalizar seu pedido, qual seu nome?", "ASK_CLIENT_NAME", data
        )

    def _log_pedido(self, data: Dict):
        import datetime
        import os
        safe_nome = str(data.get("nome_cliente", "")).replace("\n", " ").replace("\r", " ")
        safe_contato = bool(data.get("pode_contato"))
        safe_endereco = str(data.get("endereco_parcial", "")).replace("\n", " ").replace("\r", " ")
        log_line = (
            f"[{datetime.datetime.now().isoformat()}] Pedido criado: "
            f"nome={safe_nome!r} contato_permitido={safe_contato} "
            f"endereco={safe_endereco!r}"
        )
        os.makedirs("out", exist_ok=True)
        with open("out/pedidos.log", "a", encoding="utf-8") as f:
            f.write(log_line + "\n")

    # Mapeamento de variantes por palavra-chave no nome do produto.
    # Adicione entradas aqui para suportar novos produtos com variantes.
    _VARIANT_MAP = {
        "dipirona": ["comprimido", "gotas"],
        "amoxicilina": ["capsula 500mg", "suspensao"],
        "vitamina c": ["comprimido", "efervescente"],
        "ibuprofeno": ["comprimido", "suspensao"],
        "omeprazol": ["capsula 20mg", "capsula 40mg"],
    }

    def _variants_for(self, produto: ProdutoInfo) -> List[str]:
        nome = _normalize(produto.nome)
        for keyword, variantes in self._VARIANT_MAP.items():
            if keyword in nome:
                return variantes
        return []

    def _to_dict(self, produto: ProdutoInfo) -> Dict:
        return {
            "sku": produto.sku,
            "nome": produto.nome,
            "categoria": produto.categoria,
            "preco": produto.preco,
            "estoque": produto.estoque,
            "reservado": produto.reservado,
        }

    def _from_dict(self, raw: Dict) -> ProdutoInfo:
        return ProdutoInfo(
            sku=raw.get("sku", ""),
            nome=raw.get("nome", ""),
            categoria=raw.get("categoria", ""),
            preco=float(raw.get("preco", 0.0)),
            estoque=int(raw.get("estoque", 0)),
            reservado=int(raw.get("reservado", 0)),
        )
