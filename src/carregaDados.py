import json
from pathlib import Path

CAMINHO_PADRAO = Path(__file__).parent.parent / "data" / "disciplinas.json"


def carregar_disciplinas(caminho=None):
    caminho = Path(caminho) if caminho else CAMINHO_PADRAO
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)
