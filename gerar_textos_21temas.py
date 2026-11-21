# -*- coding: utf-8 -*-
"""
gerar_textos_21temas.py — transforma o ebook "21 Temas Cativantes"
(Curiosidade Gera Fluência) em textos de estudo de inglês em 3 níveis,
salvos num SQLite, prontos para alimentar o AnkiAudio.

Fluxo:
  1) Parseia o PDF: 21 temas -> subseções -> ideias/títulos (bullets em inglês).
  2) Para cada ideia, pede ao Gemini um texto curto em inglês + tradução em PT
     ALINHADA FRASE A FRASE (mesmo nº de frases), em 3 níveis:
     básico / intermediário / avançado.
  3) Salva no SQLite (tema, subsecao, caso, nivel, texto_en, texto_pt, criado_em).
  4) (Opcional, --anki) gera o .apkg de cada texto reusando o AnkiAudio headless.

Uso:
  # 1. só parsear e listar o que o PDF tem (não gasta API):
  python gerar_textos_21temas.py --parse-only

  # 2. gerar textos (precisa da key):  GEMINI_API_KEY no ambiente
  python gerar_textos_21temas.py --tema 1                 # só o tema 1
  python gerar_textos_21temas.py --tema 1 --max-ideias 2  # amostra: 2 ideias do tema 1
  python gerar_textos_21temas.py --todos                  # todos os 21 temas (gasta API!)

  # 3. também já gerar os baralhos .apkg (edge-tts, demora):
  python gerar_textos_21temas.py --tema 1 --max-ideias 1 --anki

A key vem da variável de ambiente GEMINI_API_KEY (ou GOOGLE_API_KEY).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

# ------------------------------------------------------------------ caminhos
AQUI = Path(__file__).resolve().parent
PDF_PADRAO = AQUI / "dist" / "AnkiAudio_v2_final" / "21_Temas_Cativantes.pdf"
DB_PADRAO = AQUI / "textos_21temas.db"
KEY_FILE = AQUI / ".gemini_key"  # arquivo local (gitignored) com a key numa linha


def ler_api_key() -> str | None:
    """Ordem: env GEMINI_API_KEY/GOOGLE_API_KEY, depois o arquivo .gemini_key."""
    k = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if k:
        return k.strip()
    if KEY_FILE.exists():
        txt = KEY_FILE.read_text(encoding="utf-8").strip()
        # ignora linhas de comentário e pega a 1ª não-vazia
        for linha in txt.splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#"):
                return linha
    return None

NIVEIS = ["basico", "intermediario", "avancado"]
NIVEL_LABEL = {
    "basico": "basic (A1-A2): short, simple words, present tense",
    "intermediario": "intermediate (B1-B2): natural everyday English, some variety of tenses",
    "avancado": "advanced (C1): richer vocabulary, idiomatic, more complex sentences",
}


# ============================================================ 1) PARSER DO PDF
def _split_sentences(text: str) -> list[str]:
    """Mesma regra do AnkiAudio (Criar_BaralhoComAudios_v2.split_sentences)."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


# cabeçalho de tema: "1. Daily Life", "5.Travel English", "21 – ✅ Bible & Faith ..."
_RE_TEMA = re.compile(r"^\s*(\d{1,2})\s*[.–—-]\s*(.+?)\s*$")
_BULLET = "•"  # •


def parse_ebook(pdf_path: Path) -> list[dict]:
    """Devolve lista de temas:
    [{numero, titulo, descricao, subsecoes:[{titulo, ideias:[str,...]}]}]
    """
    import fitz  # PyMuPDF

    doc = fitz.open(str(pdf_path))
    linhas: list[str] = []
    for pg in doc:
        for ln in pg.get_text().split("\n"):
            linhas.append(ln.rstrip())
    doc.close()

    temas: list[dict] = []
    tema_atual: dict | None = None
    sub_atual: dict | None = None
    esperado = 1          # próximo número de tema esperado (evita falsos positivos)
    aguardando_desc = False
    aguardando_bullet = False  # o próximo texto não-vazio é o alvo de um "•"

    def nova_sub(titulo: str):
        nonlocal sub_atual
        sub_atual = {"titulo": titulo, "ideias": []}
        tema_atual["subsecoes"].append(sub_atual)

    for ln in linhas:
        s = ln.strip()
        if not s:
            continue

        # --- cabeçalho de tema? (só se o número bate com o esperado) ---
        m = _RE_TEMA.match(s)
        if m and int(m.group(1)) == esperado and len(s) < 90 and _BULLET not in s:
            titulo = m.group(2)
            # limpa marcadores decorativos do título (✅, emojis, "(Só Ideias)" etc.)
            titulo = re.sub(r"[✅✔✨]", "", titulo).strip()
            titulo = re.sub(r"\s*[–—-]\s*T[íi]tulos.*$", "", titulo).strip()
            tema_atual = {"numero": esperado, "titulo": titulo,
                          "descricao": "", "subsecoes": []}
            temas.append(tema_atual)
            sub_atual = None
            esperado += 1
            aguardando_desc = True
            aguardando_bullet = False
            continue

        if tema_atual is None:
            continue  # ainda na introdução

        # --- marcador de bullet isolado: o próximo texto é uma ideia ---
        if s == _BULLET or s.startswith(_BULLET):
            resto = s[len(_BULLET):].strip() if s.startswith(_BULLET) else ""
            if resto:  # "• texto na mesma linha"
                if sub_atual is None:
                    nova_sub("Geral")
                sub_atual["ideias"].append(resto)
                aguardando_bullet = False
            else:
                aguardando_bullet = True
            aguardando_desc = False
            continue

        # --- texto que segue um "•": é a ideia ---
        if aguardando_bullet:
            if sub_atual is None:
                nova_sub("Geral")
            sub_atual["ideias"].append(s)
            aguardando_bullet = False
            continue

        # --- primeira linha não-vazia após o cabeçalho: descrição do tema ---
        if aguardando_desc:
            tema_atual["descricao"] = s
            aguardando_desc = False
            continue

        # --- caso contrário: é um cabeçalho de subseção ---
        titulo_sub = re.sub(r"^[^\w(]+", "", s).strip() or s
        nova_sub(titulo_sub)

    return temas


# =================================================================== 2) BANCO
SCHEMA = """
CREATE TABLE IF NOT EXISTS textos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tema       TEXT NOT NULL,
    subsecao   TEXT NOT NULL,
    caso       TEXT NOT NULL,
    nivel      TEXT NOT NULL,
    texto_en   TEXT NOT NULL,
    texto_pt   TEXT NOT NULL,
    n_frases   INTEGER DEFAULT 0,
    alinhado   INTEGER DEFAULT 1,
    apkg_path  TEXT DEFAULT '',
    criado_em  TEXT NOT NULL,
    UNIQUE(tema, subsecao, caso, nivel)
);
"""


@contextmanager
def conectar(db_path: Path):
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db(db_path: Path):
    with conectar(db_path) as con:
        con.executescript(SCHEMA)


def ja_existe(db_path: Path, tema, subsecao, caso, nivel) -> bool:
    with conectar(db_path) as con:
        r = con.execute(
            "SELECT 1 FROM textos WHERE tema=? AND subsecao=? AND caso=? AND nivel=?",
            (tema, subsecao, caso, nivel),
        ).fetchone()
    return r is not None


def salvar_texto(db_path: Path, tema, subsecao, caso, nivel,
                 texto_en, texto_pt, n_frases, alinhado) -> int:
    with conectar(db_path) as con:
        cur = con.execute(
            """INSERT INTO textos
               (tema, subsecao, caso, nivel, texto_en, texto_pt,
                n_frases, alinhado, criado_em)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(tema, subsecao, caso, nivel) DO UPDATE SET
                 texto_en=excluded.texto_en, texto_pt=excluded.texto_pt,
                 n_frases=excluded.n_frases, alinhado=excluded.alinhado,
                 criado_em=excluded.criado_em""",
            (tema, subsecao, caso, nivel, texto_en, texto_pt,
             n_frases, 1 if alinhado else 0, datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def set_apkg(db_path: Path, tema, subsecao, caso, nivel, apkg_path):
    with conectar(db_path) as con:
        con.execute(
            "UPDATE textos SET apkg_path=? WHERE tema=? AND subsecao=? AND caso=? AND nivel=?",
            (apkg_path, tema, subsecao, caso, nivel),
        )


# =================================================================== 3) GEMINI
_PROMPT = """You are an English teacher creating study material for a Brazilian learner.

Theme: {tema}
Subsection: {subsecao}
Title/idea to write about: "{caso}"
Level: {nivel}

Write a SHORT, natural, engaging text in English about that title/idea, at the given level.
Then translate it to Brazilian Portuguese.

CRITICAL RULES (an app matches each English sentence to its Portuguese sentence 1:1):
- Between 4 and 7 sentences.
- The English and the Portuguese MUST have the SAME number of sentences, in the SAME order.
- One English sentence = exactly one Portuguese sentence. Do NOT split or merge sentences.
- No lists, no bullet points, no headings, no sentence numbering. Plain prose only.
- Use a period/question/exclamation mark to end every sentence.

Return ONLY a JSON object, no markdown fences, with exactly this shape:
{{"en": "English text here.", "pt": "Texto em português aqui."}}"""


class GeminiClient:
    """Abstrai os dois SDKs: prefere google-genai (novo), cai pro antigo."""

    def __init__(self, api_key: str, modelo: str):
        self.modelo = modelo
        self._modo = None
        try:
            from google import genai  # SDK novo
            self._cli = genai.Client(api_key=api_key)
            self._modo = "novo"
        except Exception:
            import google.generativeai as gga  # SDK antigo (EOL)
            gga.configure(api_key=api_key)
            self._gga = gga
            self._model = gga.GenerativeModel(modelo)
            self._modo = "antigo"

    def gerar(self, prompt: str) -> str:
        if self._modo == "novo":
            resp = self._cli.models.generate_content(model=self.modelo, contents=prompt)
            return resp.text or ""
        resp = self._model.generate_content(prompt)
        return resp.text or ""


def _extrair_json(txt: str) -> dict:
    txt = txt.strip()
    txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt.strip(), flags=re.IGNORECASE)
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r"\{.*\}", txt, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def gerar_texto(cli: GeminiClient, tema, subsecao, caso, nivel,
                tentativas=3) -> tuple[str, str, bool]:
    """Devolve (en, pt, alinhado). Tenta realinhar o nº de frases."""
    prompt = _PROMPT.format(
        tema=tema, subsecao=subsecao, caso=caso, nivel=NIVEL_LABEL[nivel])
    ultima = ("", "")
    for i in range(1, tentativas + 1):
        try:
            raw = cli.gerar(prompt)
            data = _extrair_json(raw)
            en = (data.get("en") or "").strip()
            pt = (data.get("pt") or "").strip()
        except Exception as e:
            if i == tentativas:
                raise
            time.sleep(1.5 * i)
            continue
        ne, npt = len(_split_sentences(en)), len(_split_sentences(pt))
        ultima = (en, pt)
        if en and pt and ne == npt and ne >= 2:
            return en, pt, True
        # reforça a regra e tenta de novo
        prompt = (_PROMPT.format(tema=tema, subsecao=subsecao, caso=caso,
                                 nivel=NIVEL_LABEL[nivel])
                  + f"\n\nIMPORTANT: your last answer had {ne} English sentences but "
                    f"{npt} Portuguese ones. They MUST be equal. Rewrite it.")
        time.sleep(1.0)
    en, pt = ultima
    return en, pt, (len(_split_sentences(en)) == len(_split_sentences(pt)) and bool(en))


# ============================================================= 4) ANKI headless
_anki_app = None  # instância única reusada


def _get_anki_app():
    """Carrega o AnkiAudio em modo headless (sem diálogos bloqueantes)."""
    global _anki_app
    if _anki_app is not None:
        return _anki_app
    sys.path.insert(0, str(AQUI))
    import Criar_BaralhoComAudios_v2 as m  # noqa
    # neutraliza os diálogos que travariam o modo batch
    try:
        m.messagebox.askyesno = lambda *a, **k: False
        m.messagebox.showerror = lambda *a, **k: None
        m.messagebox.showinfo = lambda *a, **k: None
        m.messagebox.showwarning = lambda *a, **k: None
    except Exception:
        pass
    app = m.AnkiApp()
    app.withdraw()          # esconde a janela
    app.update()
    app._sem_legenda = False
    app._imersao = False
    _anki_app = (m, app)
    return _anki_app


def gerar_apkg(nome, texto_en, texto_pt) -> str | None:
    """Gera o .apkg reusando o pipeline do AnkiAudio. Devolve o caminho ou None."""
    m, app = _get_anki_app()
    frases_en = m.split_sentences(texto_en)
    frases_pt = m.split_sentences(texto_pt)
    app.cancel_event.clear()
    app.running = True
    app._pipeline(nome, texto_en, texto_pt, frases_en, frases_pt)
    for _ in range(5):
        app.update()
        time.sleep(0.05)
    pasta = os.path.join(m.OUTPUT_DIR, m.safe_name(nome))
    apkg = os.path.join(pasta, m.safe_name(nome) + ".apkg")
    return apkg if os.path.exists(apkg) else None


# ===================================================================== DRIVER
def iter_casos(temas, numero_tema=None):
    for t in temas:
        if numero_tema and t["numero"] != numero_tema:
            continue
        for sub in t["subsecoes"]:
            for ideia in sub["ideias"]:
                yield t["titulo"], sub["titulo"], ideia


def main():
    ap = argparse.ArgumentParser(description="Gera textos de estudo dos 21 Temas Cativantes.")
    ap.add_argument("--pdf", default=str(PDF_PADRAO))
    ap.add_argument("--db", default=str(DB_PADRAO))
    ap.add_argument("--parse-only", action="store_true",
                    help="só parseia o PDF e mostra o resumo (não gasta API)")
    ap.add_argument("--tema", type=int, default=None, help="número do tema (1..21)")
    ap.add_argument("--todos", action="store_true", help="processa os 21 temas")
    ap.add_argument("--max-ideias", type=int, default=None,
                    help="limita quantas ideias processar (amostra)")
    ap.add_argument("--niveis", default=",".join(NIVEIS),
                    help="níveis separados por vírgula (basico,intermediario,avancado)")
    ap.add_argument("--modelo", default=os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"))
    ap.add_argument("--anki", action="store_true", help="também gera o .apkg de cada texto")
    ap.add_argument("--pausa", type=float, default=0.5, help="pausa entre chamadas (s)")
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    db_path = Path(args.db)
    if not pdf_path.exists():
        print(f"[ERRO] PDF não encontrado: {pdf_path}")
        sys.exit(1)

    print(f"[parser] lendo {pdf_path.name} ...")
    temas = parse_ebook(pdf_path)
    tot_ideias = sum(len(s["ideias"]) for t in temas for s in t["subsecoes"])
    print(f"[parser] {len(temas)} temas, "
          f"{sum(len(t['subsecoes']) for t in temas)} subseções, "
          f"{tot_ideias} ideias.")

    if args.parse_only:
        for t in temas:
            ni = sum(len(s["ideias"]) for s in t["subsecoes"])
            print(f"  {t['numero']:>2}. {t['titulo']}  "
                  f"({len(t['subsecoes'])} subseções, {ni} ideias)")
            for s in t["subsecoes"]:
                print(f"       - {s['titulo']} [{len(s['ideias'])}]")
        return

    # --- modo geração: precisa da key ---
    api_key = ler_api_key()
    if not api_key:
        print("[ERRO] Falta a key do Gemini.")
        print(f"  Opção A: crie o arquivo {KEY_FILE} com a key numa linha.")
        print("  Opção B (PowerShell):  $env:GEMINI_API_KEY='sua_key'")
        sys.exit(2)

    if not args.todos and not args.tema:
        print("[ERRO] Diga --tema N ou --todos (ou --parse-only).")
        sys.exit(2)

    niveis = [n.strip() for n in args.niveis.split(",") if n.strip() in NIVEIS]
    init_db(db_path)
    cli = GeminiClient(api_key, args.modelo)
    print(f"[gemini] modelo={args.modelo}  modo={cli._modo}  níveis={niveis}")

    numero = None if args.todos else args.tema
    casos = list(iter_casos(temas, numero))
    if args.max_ideias:
        casos = casos[:args.max_ideias]
    total = len(casos) * len(niveis)
    print(f"[plano] {len(casos)} ideias x {len(niveis)} níveis = {total} textos.\n")

    feitos = pulados = falhas = 0
    i = 0
    for tema, subsecao, caso in casos:
        for nivel in niveis:
            i += 1
            tag = f"[{i}/{total}] {tema} > {caso[:45]} [{nivel}]"
            if ja_existe(db_path, tema, subsecao, caso, nivel):
                print(tag, "-> já existe, pulando")
                pulados += 1
                continue
            try:
                en, pt, ok = gerar_texto(cli, tema, subsecao, caso, nivel)
            except Exception as e:
                print(tag, f"-> ERRO Gemini: {e}")
                falhas += 1
                continue
            if not en or not pt:
                print(tag, "-> resposta vazia, pulando")
                falhas += 1
                continue
            nfr = len(_split_sentences(en))
            salvar_texto(db_path, tema, subsecao, caso, nivel, en, pt, nfr, ok)
            flag = "" if ok else "  (!) frases desalinhadas"
            print(tag, f"-> OK {nfr} frases{flag}")
            feitos += 1

            if args.anki and ok:
                nome = f"{tema} - {caso} ({nivel})"
                try:
                    apkg = gerar_apkg(nome, en, pt)
                    if apkg:
                        set_apkg(db_path, tema, subsecao, caso, nivel, apkg)
                        print(" " * 8, f"apkg: {apkg}")
                    else:
                        print(" " * 8, "apkg: falhou (ver logs do AnkiAudio)")
                except Exception as e:
                    print(" " * 8, f"apkg: ERRO {e}")
            time.sleep(args.pausa)

    print(f"\n[fim] gerados={feitos}  pulados={pulados}  falhas={falhas}")
    print(f"[fim] banco: {db_path}")


if __name__ == "__main__":
    main()
