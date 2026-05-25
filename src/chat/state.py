import json
import os
import sys
from dataclasses import dataclass, field
from typing import List


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatState:
    session_id: str
    messages: List[ChatMessage] = field(default_factory=list)


class SessionStore:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, session_id: str) -> str:
        safe_id = "".join(ch for ch in session_id if ch.isalnum() or ch in "-_ ").strip()
        if not safe_id:
            safe_id = "sessao"
        filename = safe_id.replace(" ", "_") + ".jsonl"
        return os.path.join(self.base_dir, filename)

    def append(self, session_id: str, role: str, content: str) -> None:
        path = self._path(session_id)
        record = {"role": role, "content": content}
        with open(path, "a", encoding="ascii") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")

    def load(self, session_id: str) -> ChatState:
        path = self._path(session_id)
        state = ChatState(session_id=session_id)
        if not os.path.exists(path):
            return state
        with open(path, "r", encoding="ascii") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    print(f"[AVISO] Linha corrompida ignorada em {path}: {line[:80]!r}", file=sys.stderr)
                    continue
                state.messages.append(
                    ChatMessage(role=record.get("role", "user"), content=record.get("content", ""))
                )
        return state

    def _state_path(self, session_id: str) -> str:
        safe_id = "".join(ch for ch in session_id if ch.isalnum() or ch in "-_ ").strip()
        if not safe_id:
            safe_id = "sessao"
        filename = safe_id.replace(" ", "_") + ".state.json"
        return os.path.join(self.base_dir, filename)

    def load_state(self, session_id: str) -> dict:
        path = self._state_path(session_id)
        if not os.path.exists(path):
            return {"state": "START", "data": {}}
        with open(path, "r", encoding="ascii") as handle:
            try:
                data = json.load(handle)
            except json.JSONDecodeError:
                return {"state": "START", "data": {}}
        return {
            "state": data.get("state", "START"),
            "data": data.get("data", {}),
        }

    def save_state(self, session_id: str, state: str, data: dict) -> None:
        path = self._state_path(session_id)
        payload = {"state": state, "data": data}
        with open(path, "w", encoding="ascii") as handle:
            json.dump(payload, handle, ensure_ascii=True)
