import importlib
import json
import urllib.request

from src.core.logging import log_event


class IntegrationAdapter:
    def on_message(self, session_id: str, message: str, state: dict) -> None:
        pass

    def on_response(self, session_id: str, response: str, state: dict) -> None:
        pass


class LocalAdapter(IntegrationAdapter):
    def __init__(self, report_dir: str) -> None:
        self.report_dir = report_dir

    def on_message(self, session_id: str, message: str, state: dict) -> None:
        log_event(self.report_dir, "chat_mensagem", {"sessao": session_id, "mensagem": message})

    def on_response(self, session_id: str, response: str, state: dict) -> None:
        log_event(self.report_dir, "chat_resposta", {"sessao": session_id, "resposta": response})


class WebhookAdapter(IntegrationAdapter):
    def __init__(self, report_dir: str, webhook_url: str) -> None:
        self.report_dir = report_dir
        self.webhook_url = webhook_url

    def _post(self, payload: dict) -> None:
        if not self.webhook_url:
            return
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()

    def on_message(self, session_id: str, message: str, state: dict) -> None:
        payload = {"tipo": "chat_mensagem", "sessao": session_id, "mensagem": message}
        self._post(payload)

    def on_response(self, session_id: str, response: str, state: dict) -> None:
        payload = {"tipo": "chat_resposta", "sessao": session_id, "resposta": response}
        self._post(payload)


def load_adapter(settings):
    adapter = (settings.integration_adapter or "local").lower().strip()
    if adapter == "local":
        return LocalAdapter(settings.report_dir)
    if adapter == "webhook":
        return WebhookAdapter(settings.report_dir, settings.integration_webhook_url)

    path = settings.integration_adapter_path
    if path:
        if ":" not in path:
            raise ValueError("Use o formato modulo:Classe em INTEGRATION_ADAPTER_PATH")
        module_name, class_name = path.split(":", 1)
        try:
            module = importlib.import_module(module_name)
            klass = getattr(module, class_name)
        except ImportError as exc:
            raise ValueError(f"Modulo '{module_name}' nao encontrado: {exc}") from exc
        except AttributeError as exc:
            raise ValueError(f"Classe '{class_name}' nao encontrada em '{module_name}': {exc}") from exc
        return klass(settings)

    return LocalAdapter(settings.report_dir)
