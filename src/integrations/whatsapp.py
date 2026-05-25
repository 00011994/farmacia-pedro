import os
import warnings


class WhatsAppIntegration:
    """
    Stub de integração com WhatsApp. Nenhuma mensagem real é enviada.

    Para ativar: implemente send_message() com a API do seu provedor
    (ex: Z-API, WPPConnect, Twilio, Evolution API) e remova o aviso abaixo.

    Variáveis de ambiente:
      WHATSAPP_NUMBER   - número remetente
      WHATSAPP_TOKEN    - token de autenticação do provedor
      WHATSAPP_PROVIDER - nome do provedor (ex: wppconnect, z-api)
    """

    def __init__(self, number=None, token=None, provider=None):
        self.number = number or os.getenv("WHATSAPP_NUMBER")
        self.token = token or os.getenv("WHATSAPP_TOKEN")
        self.provider = provider or os.getenv("WHATSAPP_PROVIDER", "wppconnect")
        if not self.token:
            warnings.warn(
                "WhatsAppIntegration: WHATSAPP_TOKEN nao configurado — mensagens nao serao enviadas.",
                stacklevel=2,
            )

    def send_message(self, to: str, text: str) -> bool:
        if not self.token:
            print(f"[WhatsApp STUB] Para {to}: {text}")
            return False
        # Substitua o bloco abaixo pela chamada real ao seu provedor.
        # Exemplo com Z-API:
        #   import urllib.request, json
        #   url = f"https://api.z-api.io/instances/.../token/.../send-text"
        #   payload = json.dumps({"phone": to, "message": text}).encode()
        #   req = urllib.request.Request(url, data=payload,
        #             headers={"Content-Type": "application/json",
        #                      "Client-Token": self.token}, method="POST")
        #   with urllib.request.urlopen(req, timeout=10) as resp:
        #       return resp.status == 200
        raise NotImplementedError(
            "Implemente send_message() com a API do seu provedor WhatsApp."
        )

    def update_number(self, new_number: str) -> None:
        self.number = new_number

    def get_number(self) -> str:
        return self.number
