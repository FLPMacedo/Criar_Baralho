# -*- coding: utf-8 -*-
"""Camada de dados do AnkiAudio (SQLite).

Guarda os projetos (textos EN/PT + vozes), a biblioteca de baralhos gerados e a
config do app. Separa a persistência da UI, no mesmo espírito do Serenus.

Uso rápido:
    import db
    db.init_db()
    pid = db.salvar_projeto("Rotina", texto_en="...", texto_pt="...", voz_en="en-US-AriaNeural", voz_pt="pt-BR-FranciscaNeural", rate=-10)
    db.listar_projetos()
    db.registrar_baralho(pid, "Rotina", "output/Rotina/Rotina.apkg", n_cards=20)
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_FILE = os.environ.get("ANKIAUDIO_DB", "ankiaudio.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS projetos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT NOT NULL,
    texto_en      TEXT DEFAULT '',
    texto_pt      TEXT DEFAULT '',
    voz_en        TEXT DEFAULT '',
    voz_pt        TEXT DEFAULT '',
    rate          INTEGER DEFAULT 0,
    criado_em     TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS baralhos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    projeto_id  INTEGER,
    nome        TEXT NOT NULL,
    apkg_path   TEXT DEFAULT '',
    n_cards     INTEGER DEFAULT 0,
    gerado_em   TEXT NOT NULL,
    FOREIGN KEY (projeto_id) REFERENCES projetos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS config (
    chave TEXT PRIMARY KEY,
    valor TEXT
);
"""


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def conectar(path: str | None = None):
    """Abre a conexão, faz commit no sucesso e SEMPRE fecha (sem vazar handle)."""
    con = sqlite3.connect(path or DB_FILE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db(path: str | None = None) -> None:
    with conectar(path) as con:
        con.executescript(SCHEMA)


# ------------------------------------------------------------------ projetos
def salvar_projeto(nome, texto_en="", texto_pt="", voz_en="", voz_pt="", rate=0,
                   projeto_id=None, path=None) -> int:
    """Cria (projeto_id=None) ou atualiza um projeto. Devolve o id."""
    agora = _agora()
    with conectar(path) as con:
        if projeto_id is None:
            cur = con.execute(
                """INSERT INTO projetos
                   (nome, texto_en, texto_pt, voz_en, voz_pt, rate, criado_em, atualizado_em)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (nome, texto_en, texto_pt, voz_en, voz_pt, rate, agora, agora),
            )
            return cur.lastrowid
        con.execute(
            """UPDATE projetos SET nome=?, texto_en=?, texto_pt=?, voz_en=?, voz_pt=?,
               rate=?, atualizado_em=? WHERE id=?""",
            (nome, texto_en, texto_pt, voz_en, voz_pt, rate, agora, projeto_id),
        )
        return projeto_id


def listar_projetos(path=None) -> list[dict]:
    with conectar(path) as con:
        rows = con.execute(
            "SELECT * FROM projetos ORDER BY atualizado_em DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def obter_projeto(projeto_id, path=None) -> dict | None:
    with conectar(path) as con:
        r = con.execute("SELECT * FROM projetos WHERE id=?", (projeto_id,)).fetchone()
    return dict(r) if r else None


def excluir_projeto(projeto_id, path=None) -> None:
    with conectar(path) as con:
        con.execute("DELETE FROM projetos WHERE id=?", (projeto_id,))


# ------------------------------------------------------------------ baralhos
def registrar_baralho(projeto_id, nome, apkg_path="", n_cards=0, path=None) -> int:
    with conectar(path) as con:
        cur = con.execute(
            """INSERT INTO baralhos (projeto_id, nome, apkg_path, n_cards, gerado_em)
               VALUES (?,?,?,?,?)""",
            (projeto_id, nome, apkg_path, n_cards, _agora()),
        )
        return cur.lastrowid


def listar_baralhos(projeto_id=None, path=None) -> list[dict]:
    with conectar(path) as con:
        if projeto_id is None:
            rows = con.execute("SELECT * FROM baralhos ORDER BY gerado_em DESC").fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM baralhos WHERE projeto_id=? ORDER BY gerado_em DESC",
                (projeto_id,),
            ).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------ config
def get_config(chave, default=None, path=None):
    with conectar(path) as con:
        r = con.execute("SELECT valor FROM config WHERE chave=?", (chave,)).fetchone()
    return r["valor"] if r else default


def set_config(chave, valor, path=None) -> None:
    with conectar(path) as con:
        con.execute(
            "INSERT INTO config (chave, valor) VALUES (?,?) "
            "ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",
            (chave, str(valor)),
        )


def migrar_config_json(json_path="config_v2.json", path=None) -> int:
    """Importa a config antiga do JSON pro banco (uma vez). Devolve quantas chaves migrou."""
    import json
    if not os.path.exists(json_path):
        return 0
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return 0
    n = 0
    for k, v in data.items():
        if get_config(k, path=path) is None:
            set_config(k, v, path=path)
            n += 1
    return n


# ------------------------------------------------------------------ autoteste
if __name__ == "__main__":
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "ankiaudio_test.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    init_db(tmp)
    pid = salvar_projeto("Rotina da manhã", texto_en="I wake up early.",
                         texto_pt="Eu acordo cedo.", voz_en="en-US-AriaNeural",
                         voz_pt="pt-BR-FranciscaNeural", rate=-10, path=tmp)
    salvar_projeto("Rotina da manhã (editado)", texto_en="I wake up at six.",
                   texto_pt="Eu acordo às seis.", projeto_id=pid, path=tmp)
    registrar_baralho(pid, "Rotina da manhã", "output/Rotina/Rotina.apkg", 12, path=tmp)
    set_config("voice_en", "en-GB-SoniaNeural", path=tmp)
    projs = listar_projetos(tmp)
    bars = listar_baralhos(path=tmp)
    assert len(projs) == 1 and projs[0]["nome"].endswith("(editado)"), "update falhou"
    assert len(bars) == 1 and bars[0]["n_cards"] == 12, "baralho falhou"
    assert get_config("voice_en", path=tmp) == "en-GB-SoniaNeural", "config falhou"
    excluir_projeto(pid, path=tmp)
    assert listar_projetos(tmp) == [] and listar_baralhos(path=tmp) == [], "cascade falhou"
    os.remove(tmp)
    print("db.py: todos os testes passaram ✔ (projetos, baralhos, config, update, cascade)")
