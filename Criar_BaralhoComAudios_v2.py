"""
Gerador Completo Anki + Áudio - v2
- UI moderna com CustomTkinter (tema escuro, sidebar, cards arredondados)
- Vozes/velocidade configuráveis, preview de áudio, cancelar geração
- Cards reversos no Anki (EN->PT e PT->EN)
- PDF de roteiro de treino (capa, sumário, tabela, numerado, textos completos)
- Logs em arquivo + retry automático no edge-tts
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import sys
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox


def resource_path(relative: str) -> str:
    """Resolve caminhos tanto rodando .py quanto empacotado pelo PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, relative)


# Diretório base do app: ao lado do .exe (empacotado) ou do .py (dev). Tudo que
# o app grava (output, logs, config, banco) fica ancorado AQUI — não no diretório
# de trabalho, que muda conforme como o exe é aberto.
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("ANKIAUDIO_DB", os.path.join(APP_DIR, "ankiaudio.db"))

import customtkinter as ctk
import edge_tts
import genanki
import pygame

import db  # v3: camada de dados (SQLite)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# =========================
# CONFIGURAÇÕES GLOBAIS
# =========================
AUTOR = "@UaiScript"
CANAL_URL = "https://www.youtube.com/@UaiScript"
OUTPUT_DIR = os.path.join(APP_DIR, "output")  # sempre ao lado do exe
LOGS_DIR = os.path.join(APP_DIR, "logs")
CONFIG_FILE = os.path.join(APP_DIR, "config_v2.json")
MODEL_ID = 7894561231  # diferente da v1

DEFAULT_CONFIG = {
    "voice_en": "en-US-AriaNeural",
    "voice_pt": "pt-BR-FranciscaNeural",
    "rate": -10,  # percentual
    "autor": AUTOR,
}

# Lista de bônus exibidos no módulo "Bônus". Cada entrada aponta para um
# arquivo dentro de assets/bonus/ (resolvido por resource_path).
BONUS_ITEMS = [
    {
        "file": "BizuDeck.exe",
        "icon": "🧠",
        "title": "BizuDeck — App de Quiz (bônus)",
        "subtitle": "Quiz com áudio pra concursos e faculdade",
        "desc": (
            "App completo de brinde: gere quizzes com áudio a partir de "
            "qualquer texto (formato P>/R>), estude no modo interativo e "
            "exporte pro Anki. Clique em 'Abrir agora' para rodar o BizuDeck."
        ),
    },
    {
        "file": "Material_DestravarIngles.pdf",
        "icon": "📄",
        "title": "Como Destravar o Inglês",
        "subtitle": "Método + cronograma de 30 dias",
        "desc": (
            "PDF completo com o método de imersão por áudio bilíngue, "
            "tutorial passo a passo do app, cronograma de estudo e os "
            "erros que mantêm você travado."
        ),
    },
    {
        "file": "21_Temas_Cativantes.pdf",
        "icon": "🎯",
        "title": "21 Temas Cativantes",
        "subtitle": "Curiosidade gera fluência",
        "desc": (
            "Ebook com 21 temas modernos prontos para virar textos e "
            "flashcards — rotina, esportes, viagens, cinema, finanças, "
            "música, fé e muito mais. Centenas de títulos em inglês."
        ),
    },
]

VOICES_EN = [
    # US — Femininas
    "en-US-AriaNeural",
    "en-US-JennyNeural",
    "en-US-AnaNeural",
    "en-US-EmmaNeural",
    "en-US-AvaNeural",
    "en-US-MichelleNeural",
    # US — Masculinas
    "en-US-GuyNeural",
    "en-US-ChristopherNeural",
    "en-US-EricNeural",
    "en-US-AndrewNeural",
    "en-US-BrianNeural",
    "en-US-RogerNeural",
    "en-US-SteffanNeural",
    # UK
    "en-GB-SoniaNeural",
    "en-GB-LibbyNeural",
    "en-GB-MaisieNeural",
    "en-GB-RyanNeural",
    "en-GB-ThomasNeural",
    # Austrália
    "en-AU-NatashaNeural",
]
VOICES_PT = [
    "pt-BR-FranciscaNeural",
    "pt-BR-AntonioNeural",
    "pt-BR-ThalitaMultilingualNeural",
]

# Paleta (inspirada em apps tipo Serenus/H2Team: escuro com acento verde-água)
COLOR_BG = "#0f1419"
COLOR_SIDEBAR = "#161b22"
COLOR_CARD = "#1c2128"
COLOR_CARD_HOVER = "#22272e"
COLOR_ACCENT = "#2ea88a"
COLOR_ACCENT_HOVER = "#39c4a3"
COLOR_DANGER = "#e5534b"
COLOR_TEXT = "#e6edf3"
COLOR_TEXT_DIM = "#8b949e"
COLOR_BORDER = "#30363d"

FONT_TITLE = ("Segoe UI Semibold", 22)
FONT_H2 = ("Segoe UI Semibold", 16)
FONT_LABEL = ("Segoe UI", 12)
FONT_INPUT = ("Segoe UI", 13)
FONT_BTN = ("Segoe UI Semibold", 13)
FONT_SIDEBAR = ("Segoe UI", 14)

# =========================
# LOGGING
# =========================
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, "v2.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
)
log = logging.getLogger("anki_v2")


# =========================
# CONFIG PERSISTENTE
# =========================
def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = {**DEFAULT_CONFIG, **data}
            # Limpa campos legados (versões antigas tinham PDFs bônus na config)
            cfg.pop("pdf_bonus", None)
            cfg.pop("pdf_bonus_list", None)
            return cfg
        except Exception as e:
            log.warning(f"Falha ao ler config: {e}. Usando padrão.")
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# =========================
# HELPERS
# =========================
def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def safe_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "", name.replace(" ", "_"))


def format_rate(rate_int: int) -> str:
    sign = "+" if rate_int >= 0 else ""
    return f"{sign}{rate_int}%"


async def gerar_audio_async(
    texto: str, voz: str, caminho: str, rate: str, cancel: threading.Event,
    max_retries: int = 3,
) -> None:
    """Gera áudio com retry. Lança CancelledError se o usuário cancelou."""
    for attempt in range(1, max_retries + 1):
        if cancel.is_set():
            raise asyncio.CancelledError("Cancelado pelo usuário")
        try:
            tts = edge_tts.Communicate(texto, voice=voz, rate=rate)
            await tts.save(caminho)
            return
        except Exception as e:
            log.warning(f"Tentativa {attempt}/{max_retries} falhou para {caminho}: {e}")
            if attempt == max_retries:
                log.error(f"Falha definitiva ao gerar {caminho}")
                msg = str(e)
                if ("403" in msg or "Invalid response status" in msg
                        or "handshake" in msg.lower()):
                    raise RuntimeError(
                        "O serviço de voz (edge-tts) recusou a conexão (403).\n\n"
                        "Isso acontece quando a Microsoft muda o token de "
                        "autenticação e a versão do edge-tts fica desatualizada.\n\n"
                        "Solução: atualize o edge-tts com\n"
                        "    pip install -U edge-tts\n"
                        "ou baixe a versão mais nova do app."
                    ) from e
                raise
            await asyncio.sleep(1.5 * attempt)


# =========================
# APLICAÇÃO PRINCIPAL
# =========================
class AnkiApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config_data = load_config()
        db.init_db()  # v3: garante o banco de dados (projetos, baralhos)

        self.title("Gerador Anki + Áudio — v2")
        self.geometry("1180x780")
        self.minsize(1050, 720)
        self.configure(fg_color=COLOR_BG)

        ctk.set_appearance_mode("dark")

        try:
            ico = resource_path("assets/uaiscript.ico")
            if os.path.exists(ico):
                self.iconbitmap(ico)
        except Exception as e:
            log.warning(f"Falha ao definir ícone: {e}")

        # estado do pipeline
        self.cancel_event = threading.Event()
        self.running = False

        try:
            pygame.mixer.init()
        except Exception as e:
            log.warning(f"pygame.mixer falhou: {e}")

        self._build_layout()
        self._show_view("criar")

    # -------- layout principal --------
    def _build_layout(self):
        # Sidebar
        self.sidebar = ctk.CTkFrame(
            self, fg_color=COLOR_SIDEBAR, corner_radius=0, width=240
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text="ANKI + ÁUDIO",
            font=("Segoe UI Semibold", 18),
            text_color=COLOR_ACCENT,
        ).pack(pady=(30, 6), padx=20, anchor="w")
        ctk.CTkLabel(
            self.sidebar,
            text="v2",
            font=("Segoe UI", 11),
            text_color=COLOR_TEXT_DIM,
        ).pack(padx=20, anchor="w")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLOR_BORDER).pack(
            fill="x", padx=20, pady=22
        )

        self.nav_buttons = {}
        for key, label, icon in [
            ("criar", "Criar Baralho", "▶"),
            ("biblioteca", "Meus Baralhos", "📚"),
            ("bonus", "Bônus", "🎁"),
            ("config", "Configurações", "⚙"),
            ("sobre", "Sobre", "ℹ"),
        ]:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {icon}   {label}",
                anchor="w",
                font=FONT_SIDEBAR,
                fg_color="transparent",
                hover_color=COLOR_CARD_HOVER,
                text_color=COLOR_TEXT,
                corner_radius=8,
                height=42,
                command=lambda k=key: self._show_view(k),
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = btn

        rodape = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", pady=14, padx=12)
        ctk.CTkButton(
            rodape,
            text=f"▶  {AUTOR}",
            font=("Segoe UI Semibold", 12),
            fg_color="transparent",
            hover_color=COLOR_CARD_HOVER,
            text_color=COLOR_ACCENT,
            anchor="w",
            height=34,
            corner_radius=8,
            command=lambda: webbrowser.open(CANAL_URL),
        ).pack(fill="x")
        ctk.CTkLabel(
            rodape,
            text="Inscreva-se no YouTube",
            font=("Segoe UI", 9),
            text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w", padx=10)

        # Área principal (container das views)
        self.main = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self.main.pack(side="right", fill="both", expand=True)

        self.views = {
            "criar": self._build_view_criar(),
            "biblioteca": self._build_view_biblioteca(),
            "bonus": self._build_view_bonus(),
            "config": self._build_view_config(),
            "sobre": self._build_view_sobre(),
        }

    def _show_view(self, key: str):
        for v in self.views.values():
            v.pack_forget()
        self.views[key].pack(fill="both", expand=True, padx=24, pady=20)
        if key == "biblioteca":
            self._refresh_biblioteca()
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=COLOR_CARD, text_color=COLOR_ACCENT)
            else:
                btn.configure(fg_color="transparent", text_color=COLOR_TEXT)

    # -------- helpers de UI --------
    def _card(self, parent) -> ctk.CTkFrame:
        return ctk.CTkFrame(
            parent,
            fg_color=COLOR_CARD,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER,
        )

    # -------- VIEW: CRIAR --------
    def _build_view_criar(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.main, fg_color="transparent")

        # Cabeçalho
        header = ctk.CTkFrame(view, fg_color="transparent")
        header.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(
            header,
            text="Criar Baralho",
            font=FONT_TITLE,
            text_color=COLOR_TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Cole seus textos em inglês e português. Cada frase deve corresponder em ambos.",
            font=FONT_LABEL,
            text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w", pady=(2, 0))

        # Card: Nome
        card_nome = self._card(view)
        card_nome.pack(fill="x", pady=8)
        ctk.CTkLabel(
            card_nome,
            text="Nome do Baralho",
            font=FONT_H2,
            text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=18, pady=(14, 6))
        self.entry_nome = ctk.CTkEntry(
            card_nome,
            placeholder_text="Ex.: Inglês básico - Lição 01",
            font=FONT_INPUT,
            height=38,
            border_color=COLOR_BORDER,
        )
        self.entry_nome.pack(fill="x", padx=18, pady=(0, 16))

        # Card: Textos (EN + PT lado a lado)
        card_textos = self._card(view)
        card_textos.pack(fill="both", expand=True, pady=8)
        card_textos.grid_columnconfigure(0, weight=1)
        card_textos.grid_columnconfigure(1, weight=1)
        card_textos.grid_rowconfigure(1, weight=1)

        # Cabeçalho EN
        head_en = ctk.CTkFrame(card_textos, fg_color="transparent")
        head_en.grid(row=0, column=0, sticky="ew", padx=(18, 9), pady=(14, 6))
        ctk.CTkLabel(
            head_en, text="Texto em INGLÊS", font=FONT_H2, text_color=COLOR_TEXT
        ).pack(side="left")
        ctk.CTkButton(
            head_en, text="Importar .txt", width=110, height=28,
            font=("Segoe UI", 11), fg_color=COLOR_CARD_HOVER,
            hover_color=COLOR_BORDER, text_color=COLOR_TEXT,
            command=lambda: self._importar_txt(self.txt_en),
        ).pack(side="right")

        # Cabeçalho PT
        head_pt = ctk.CTkFrame(card_textos, fg_color="transparent")
        head_pt.grid(row=0, column=1, sticky="ew", padx=(9, 18), pady=(14, 6))
        ctk.CTkLabel(
            head_pt, text="Texto em PORTUGUÊS", font=FONT_H2, text_color=COLOR_TEXT
        ).pack(side="left")
        ctk.CTkButton(
            head_pt, text="Importar .txt", width=110, height=28,
            font=("Segoe UI", 11), fg_color=COLOR_CARD_HOVER,
            hover_color=COLOR_BORDER, text_color=COLOR_TEXT,
            command=lambda: self._importar_txt(self.txt_pt),
        ).pack(side="right")

        self.txt_en = ctk.CTkTextbox(
            card_textos, font=FONT_INPUT, fg_color=COLOR_BG,
            border_color=COLOR_BORDER, border_width=1, corner_radius=8,
            wrap="word",
        )
        self.txt_en.grid(row=1, column=0, sticky="nsew", padx=(18, 9), pady=(0, 8))

        self.txt_pt = ctk.CTkTextbox(
            card_textos, font=FONT_INPUT, fg_color=COLOR_BG,
            border_color=COLOR_BORDER, border_width=1, corner_radius=8,
            wrap="word",
        )
        self.txt_pt.grid(row=1, column=1, sticky="nsew", padx=(9, 18), pady=(0, 8))

        # Linha de contadores + preview
        rodape_textos = ctk.CTkFrame(card_textos, fg_color="transparent")
        rodape_textos.grid(row=2, column=0, columnspan=2, sticky="ew",
                           padx=18, pady=(0, 14))
        self.lbl_contador = ctk.CTkLabel(
            rodape_textos, text="EN: 0 frases  •  PT: 0 frases",
            font=FONT_LABEL, text_color=COLOR_TEXT_DIM,
        )
        self.lbl_contador.pack(side="left")
        ctk.CTkButton(
            rodape_textos, text="🔊 Testar voz EN",
            font=("Segoe UI", 11), height=28, width=120,
            fg_color=COLOR_CARD_HOVER, hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            command=lambda: self._preview("en"),
        ).pack(side="right", padx=4)
        ctk.CTkButton(
            rodape_textos, text="🔊 Testar voz PT",
            font=("Segoe UI", 11), height=28, width=120,
            fg_color=COLOR_CARD_HOVER, hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            command=lambda: self._preview("pt"),
        ).pack(side="right", padx=4)

        # Atualizar contadores ao digitar
        self.txt_en.bind("<KeyRelease>", lambda e: self._atualizar_contador())
        self.txt_pt.bind("<KeyRelease>", lambda e: self._atualizar_contador())

        # Card: progresso + ações
        card_acoes = self._card(view)
        card_acoes.pack(fill="x", pady=8)
        self.progress = ctk.CTkProgressBar(
            card_acoes, height=12, progress_color=COLOR_ACCENT,
            fg_color=COLOR_BG, corner_radius=6,
        )
        self.progress.set(0)
        self.progress.pack(fill="x", padx=18, pady=(16, 6))
        self.lbl_status = ctk.CTkLabel(
            card_acoes, text="Aguardando…",
            font=FONT_LABEL, text_color=COLOR_TEXT_DIM,
        )
        self.lbl_status.pack(anchor="w", padx=18)

        self.lbl_tresvel = ctk.CTkLabel(
            card_acoes,
            text="🐢 ▶ 🐇  Todo baralho já vem em 3 velocidades (lento / médio "
                 "automático / rápido).",
            font=FONT_LABEL, text_color=COLOR_TEXT_DIM, anchor="w", justify="left",
        )
        self.lbl_tresvel.pack(anchor="w", padx=18, pady=(10, 2))

        self.chk_escuta = ctk.CTkCheckBox(
            card_acoes,
            text="🎧  Sem o texto em inglês (escuta) — a frente mostra só o áudio; "
                 "o inglês aparece na resposta",
            font=FONT_LABEL, text_color=COLOR_TEXT_DIM,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            checkbox_width=20, checkbox_height=20,
        )
        self.chk_escuta.pack(anchor="w", padx=18, pady=(8, 0))

        self.chk_imersao = ctk.CTkCheckBox(
            card_acoes,
            text="🌊  Imersão — na resposta o português fica oculto (clique na "
                 "setinha pra ver) e sem áudio em PT",
            font=FONT_LABEL, text_color=COLOR_TEXT_DIM,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            checkbox_width=20, checkbox_height=20,
        )
        self.chk_imersao.pack(anchor="w", padx=18, pady=(8, 0))

        botoes = ctk.CTkFrame(card_acoes, fg_color="transparent")
        botoes.pack(fill="x", padx=14, pady=14)
        self.btn_gerar = ctk.CTkButton(
            botoes, text="🚀  Gerar Projeto + Baralho + PDF",
            font=FONT_BTN, height=46,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            text_color="#0b1d18", corner_radius=10,
            command=self._iniciar_geracao,
        )
        self.btn_gerar.pack(side="left", fill="x", expand=True, padx=4)
        self.btn_cancelar = ctk.CTkButton(
            botoes, text="✕  Cancelar",
            font=FONT_BTN, height=46, width=160,
            fg_color="transparent", border_width=1, border_color=COLOR_DANGER,
            hover_color="#3a1f1d", text_color=COLOR_DANGER,
            corner_radius=10, state="disabled",
            command=self._cancelar,
        )
        self.btn_cancelar.pack(side="right", padx=4)

        return view

    # -------- VIEW: MEUS BARALHOS (v3) --------
    def _build_view_biblioteca(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.main, fg_color="transparent")
        ctk.CTkLabel(
            view, text="Meus Baralhos", font=FONT_TITLE, text_color=COLOR_TEXT
        ).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            view,
            text="Seus projetos salvos. Reabra pra editar os textos e gerar o baralho de novo.",
            font=FONT_LABEL, text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w", pady=(0, 14))
        self.biblioteca_scroll = ctk.CTkScrollableFrame(view, fg_color="transparent")
        self.biblioteca_scroll.pack(fill="both", expand=True)
        return view

    def _refresh_biblioteca(self):
        for w in self.biblioteca_scroll.winfo_children():
            w.destroy()
        try:
            projetos = db.listar_projetos()
        except Exception:
            log.exception("Falha ao listar projetos")
            projetos = []
        if not projetos:
            ctk.CTkLabel(
                self.biblioteca_scroll,
                text="Nenhum projeto salvo ainda.\n\nGere um baralho na aba "
                     "'Criar Baralho' — ele aparece aqui automaticamente.",
                font=FONT_LABEL, text_color=COLOR_TEXT_DIM, justify="left",
            ).pack(anchor="w", padx=6, pady=20)
            return
        for p in projetos:
            card = self._card(self.biblioteca_scroll)
            card.pack(fill="x", pady=6)
            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(fill="x", padx=16, pady=(14, 2))
            ctk.CTkLabel(
                info, text=p["nome"], font=("Segoe UI Semibold", 16),
                text_color=COLOR_TEXT, anchor="w",
            ).pack(anchor="w")
            n_en = len(split_sentences(p.get("texto_en") or ""))
            n_bar = len(db.listar_baralhos(p["id"]))
            ctk.CTkLabel(
                info,
                text=f"{n_en} frases · {n_bar} baralho(s) gerado(s) · "
                     f"atualizado {str(p['atualizado_em'])[:10]}",
                font=("Segoe UI", 11), text_color=COLOR_TEXT_DIM, anchor="w",
            ).pack(anchor="w")
            botoes = ctk.CTkFrame(card, fg_color="transparent")
            botoes.pack(fill="x", padx=12, pady=(6, 12))
            ctk.CTkButton(
                botoes, text="✏  Abrir", width=110, height=34,
                font=("Segoe UI Semibold", 12), fg_color=COLOR_ACCENT,
                hover_color=COLOR_ACCENT_HOVER, text_color="#0b1d18",
                corner_radius=8, command=lambda pr=p: self._carregar_projeto(pr),
            ).pack(side="left", padx=4)
            ctk.CTkButton(
                botoes, text="🗑  Excluir", width=110, height=34,
                font=("Segoe UI", 12), fg_color="transparent", border_width=1,
                border_color=COLOR_DANGER, hover_color="#3a1f1d",
                text_color=COLOR_DANGER, corner_radius=8,
                command=lambda pr=p: self._excluir_projeto(pr),
            ).pack(side="left", padx=4)

    def _carregar_projeto(self, proj):
        self.entry_nome.delete(0, "end")
        self.entry_nome.insert(0, proj["nome"])
        self.txt_en.delete("1.0", "end")
        self.txt_en.insert("1.0", proj.get("texto_en") or "")
        self.txt_pt.delete("1.0", "end")
        self.txt_pt.insert("1.0", proj.get("texto_pt") or "")
        self._atualizar_contador()
        self._show_view("criar")
        self._status(f"Projeto '{proj['nome']}' carregado.")

    def _excluir_projeto(self, proj):
        if not messagebox.askyesno(
            "Excluir",
            f"Excluir o projeto '{proj['nome']}' da biblioteca?\n\n"
            "(Os arquivos já gerados em disco NÃO são apagados.)",
        ):
            return
        try:
            db.excluir_projeto(proj["id"])
            self._refresh_biblioteca()
        except Exception as e:
            log.exception("Falha ao excluir projeto")
            messagebox.showerror("Erro", str(e))

    # -------- VIEW: CONFIG --------
    def _build_view_config(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.main, fg_color="transparent")

        ctk.CTkLabel(
            view, text="Configurações", font=FONT_TITLE, text_color=COLOR_TEXT
        ).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            view, text="Vozes e velocidade do áudio gerado pelo Edge TTS.",
            font=FONT_LABEL, text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w", pady=(0, 14))

        card = self._card(view)
        card.pack(fill="x", pady=8)

        # Voz EN
        ctk.CTkLabel(
            card, text="Voz para INGLÊS", font=FONT_H2, text_color=COLOR_TEXT
        ).pack(anchor="w", padx=18, pady=(16, 4))
        self.combo_voz_en = ctk.CTkOptionMenu(
            card, values=VOICES_EN, font=FONT_INPUT, height=36,
            fg_color=COLOR_BG, button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER, dropdown_fg_color=COLOR_CARD,
            command=lambda v: self._on_voz_selecionada("en", v),
        )
        self.combo_voz_en.set(self.config_data["voice_en"])
        self.combo_voz_en.pack(fill="x", padx=18, pady=(0, 14))

        # Voz PT
        ctk.CTkLabel(
            card, text="Voz para PORTUGUÊS", font=FONT_H2, text_color=COLOR_TEXT
        ).pack(anchor="w", padx=18, pady=(6, 4))
        self.combo_voz_pt = ctk.CTkOptionMenu(
            card, values=VOICES_PT, font=FONT_INPUT, height=36,
            fg_color=COLOR_BG, button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER, dropdown_fg_color=COLOR_CARD,
            command=lambda v: self._on_voz_selecionada("pt", v),
        )
        self.combo_voz_pt.set(self.config_data["voice_pt"])
        self.combo_voz_pt.pack(fill="x", padx=18, pady=(0, 14))

        # Velocidade
        velo_row = ctk.CTkFrame(card, fg_color="transparent")
        velo_row.pack(fill="x", padx=18, pady=(6, 18))
        ctk.CTkLabel(
            velo_row, text="Velocidade", font=FONT_H2, text_color=COLOR_TEXT
        ).pack(side="left")
        self.lbl_velo = ctk.CTkLabel(
            velo_row, text=format_rate(self.config_data["rate"]),
            font=FONT_H2, text_color=COLOR_ACCENT,
        )
        self.lbl_velo.pack(side="right")
        self.slider_velo = ctk.CTkSlider(
            card, from_=-50, to=50, number_of_steps=20,
            progress_color=COLOR_ACCENT, button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER,
            command=self._on_velo_change,
        )
        self.slider_velo.set(self.config_data["rate"])
        self.slider_velo.pack(fill="x", padx=18, pady=(0, 18))

        # Autor
        card_autor = self._card(view)
        card_autor.pack(fill="x", pady=8)
        ctk.CTkLabel(
            card_autor, text="Autor (rodapé dos cards)",
            font=FONT_H2, text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=18, pady=(16, 6))
        self.entry_autor = ctk.CTkEntry(
            card_autor, font=FONT_INPUT, height=36,
            border_color=COLOR_BORDER,
        )
        self.entry_autor.insert(0, self.config_data["autor"])
        self.entry_autor.bind("<FocusOut>", lambda e: self._salvar_config())
        self.entry_autor.pack(fill="x", padx=18, pady=(0, 16))

        return view

    # -------- VIEW: BÔNUS --------
    def _build_view_bonus(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.main, fg_color="transparent")

        ctk.CTkLabel(
            view, text="🎁  Bônus", font=FONT_TITLE, text_color=COLOR_TEXT
        ).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            view,
            text="Materiais gratuitos do canal @UaiScript para acelerar "
                 "seu aprendizado. Baixe e use à vontade.",
            font=FONT_LABEL, text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w", pady=(0, 14))

        for item in BONUS_ITEMS:
            card = self._card(view)
            card.pack(fill="x", pady=8)

            topo = ctk.CTkFrame(card, fg_color="transparent")
            topo.pack(fill="x", padx=18, pady=(16, 4))
            ctk.CTkLabel(
                topo, text=item["icon"], font=("Segoe UI", 26),
                text_color=COLOR_ACCENT,
            ).pack(side="left", padx=(0, 12))
            txt = ctk.CTkFrame(topo, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(
                txt, text=item["title"],
                font=("Segoe UI Semibold", 17), text_color=COLOR_TEXT,
                anchor="w",
            ).pack(anchor="w")
            ctk.CTkLabel(
                txt, text=item["subtitle"],
                font=("Segoe UI", 11), text_color=COLOR_ACCENT,
                anchor="w",
            ).pack(anchor="w")

            # Tamanho do arquivo (lateral direita)
            try:
                src = resource_path(f"assets/bonus/{item['file']}")
                size_mb = os.path.getsize(src) / (1024 * 1024)
                size_txt = (f"{size_mb:.1f} MB" if size_mb >= 1
                            else f"{size_mb * 1024:.0f} KB")
            except Exception:
                size_txt = "PDF"
            ctk.CTkLabel(
                topo, text=size_txt,
                font=("Segoe UI", 11), text_color=COLOR_TEXT_DIM,
            ).pack(side="right")

            ctk.CTkLabel(
                card, text=item["desc"],
                font=FONT_LABEL, text_color=COLOR_TEXT,
                justify="left", wraplength=760, anchor="w",
            ).pack(anchor="w", padx=18, pady=(8, 12))

            botoes = ctk.CTkFrame(card, fg_color="transparent")
            botoes.pack(fill="x", padx=14, pady=(0, 14))
            ctk.CTkButton(
                botoes, text="📥  Baixar PDF", height=40, width=180,
                font=FONT_BTN,
                fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
                text_color="#0b1d18", corner_radius=10,
                command=lambda it=item: self._baixar_bonus(it),
            ).pack(side="left", padx=4)
            ctk.CTkButton(
                botoes, text="👁  Abrir agora", height=40, width=160,
                font=FONT_BTN,
                fg_color="transparent", border_width=1,
                border_color=COLOR_ACCENT,
                hover_color=COLOR_CARD_HOVER, text_color=COLOR_ACCENT,
                corner_radius=10,
                command=lambda it=item: self._abrir_bonus(it),
            ).pack(side="left", padx=4)

        ctk.CTkLabel(
            view,
            text="💡  Esses materiais são distribuídos gratuitamente. "
                 "Compartilhe com quem precisa destravar o inglês.",
            font=("Segoe UI", 11), text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w", pady=(14, 0))

        return view

    def _baixar_bonus(self, item: dict):
        src = resource_path(f"assets/bonus/{item['file']}")
        if not os.path.isfile(src):
            messagebox.showerror(
                "Erro",
                f"Arquivo do bônus não encontrado:\n{item['file']}",
            )
            return
        sugestao = item["file"]
        ext = os.path.splitext(sugestao)[1] or ".pdf"
        dest = filedialog.asksaveasfilename(
            title=f"Salvar '{item['title']}' como…",
            defaultextension=ext,
            filetypes=[(ext.upper().lstrip("."), f"*{ext}"), ("Todos", "*.*")],
            initialfile=sugestao,
        )
        if not dest:
            return
        try:
            import shutil
            shutil.copy2(src, dest)
            log.info(f"Bônus baixado: {dest}")
            if messagebox.askyesno(
                "Concluído",
                f"PDF salvo em:\n{dest}\n\nAbrir agora?",
            ):
                try:
                    os.startfile(dest)
                except Exception:
                    pass
        except Exception as e:
            log.exception("Erro ao salvar bônus")
            messagebox.showerror("Erro", f"Não foi possível salvar:\n{e}")

    def _abrir_bonus(self, item: dict):
        src = resource_path(f"assets/bonus/{item['file']}")
        if not os.path.isfile(src):
            messagebox.showerror(
                "Erro",
                f"Arquivo do bônus não encontrado:\n{item['file']}",
            )
            return
        try:
            os.startfile(src)
        except Exception as e:
            log.warning(f"Falha ao abrir bônus: {e}")
            messagebox.showerror("Erro", f"Não foi possível abrir:\n{e}")

    def _on_velo_change(self, val):
        self.lbl_velo.configure(text=format_rate(int(val)))
        self._salvar_config()

    def _salvar_config(self):
        self.config_data["voice_en"] = self.combo_voz_en.get()
        self.config_data["voice_pt"] = self.combo_voz_pt.get()
        self.config_data["rate"] = int(self.slider_velo.get())
        self.config_data["autor"] = self.entry_autor.get().strip() or AUTOR
        save_config(self.config_data)

    def _on_voz_selecionada(self, idioma: str, voz: str):
        """Quando o usuário escolhe uma voz no dropdown, salva e toca
        uma frase curta de demonstração com essa voz."""
        self._salvar_config()
        self._preview_voz_selecionada(idioma, voz)

    def _preview_voz_selecionada(self, idioma: str, voz: str):
        if idioma == "en":
            texto = "Hi, this is my voice. I will read your English text."
        else:
            texto = (
                "Olá, essa é minha voz. Eu vou ler o seu texto em português."
            )
        rate = format_rate(self.config_data["rate"])

        os.makedirs(LOGS_DIR, exist_ok=True)
        ts = int(datetime.now().timestamp() * 1000)
        out = os.path.join(LOGS_DIR, f"_preview_voz_{idioma}_{ts}.mp3")

        def worker():
            try:
                self._status(f"Testando voz: {voz}…")
                # Libera áudio anterior do pygame antes de gravar
                try:
                    if pygame.mixer.get_init() is not None:
                        pygame.mixer.music.stop()
                        try:
                            pygame.mixer.music.unload()
                        except Exception:
                            pass
                except Exception:
                    pass
                ev = threading.Event()
                asyncio.run(gerar_audio_async(
                    texto, voz, out, rate, ev, max_retries=2,
                ))
                self._tocar(out)
                self._status(f"Voz {voz}")
                self._limpar_previews_antigos(out)
            except Exception as e:
                log.exception("Falha na prévia da voz")
                self._status(f"Erro: {e}")

        threading.Thread(target=worker, daemon=True).start()

    # -------- VIEW: SOBRE --------
    def _build_view_sobre(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.main, fg_color="transparent")
        ctk.CTkLabel(
            view, text="Sobre", font=FONT_TITLE, text_color=COLOR_TEXT
        ).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            view, text="Informações do aplicativo e do canal.",
            font=FONT_LABEL, text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w", pady=(0, 14))

        # Card: descrição do app
        card = self._card(view)
        card.pack(fill="x", pady=8)
        ctk.CTkLabel(
            card, text="Gerador Anki + Áudio — v2",
            font=FONT_H2, text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=18, pady=(16, 6))
        texto = (
            "• Geração de áudio (EN, PT, MIX) com Edge TTS\n"
            "• Baralho Anki .apkg com cards reversos (EN→PT e PT→EN)\n"
            "• PDF de roteiro de treino com capa, sumário, tabela bilíngue,\n"
            "  versão numerada e textos completos\n\n"
            f"Logs:  {os.path.abspath(os.path.join(LOGS_DIR, 'v2.log'))}\n"
            f"Saída: {os.path.abspath(OUTPUT_DIR)}"
        )
        ctk.CTkLabel(
            card, text=texto, font=FONT_LABEL, text_color=COLOR_TEXT,
            justify="left", anchor="w",
        ).pack(anchor="w", padx=18, pady=(0, 18))

        # Card: canal UaiScript
        canal_card = self._card(view)
        canal_card.pack(fill="x", pady=8)

        topo = ctk.CTkFrame(canal_card, fg_color="transparent")
        topo.pack(fill="x", padx=18, pady=(18, 6))
        ctk.CTkLabel(
            topo, text="Canal do desenvolvedor",
            font=FONT_H2, text_color=COLOR_TEXT,
        ).pack(side="left")
        ctk.CTkLabel(
            topo, text="YouTube",
            font=("Segoe UI", 11), text_color=COLOR_TEXT_DIM,
        ).pack(side="right")

        ctk.CTkLabel(
            canal_card, text=AUTOR,
            font=("Segoe UI Semibold", 20), text_color=COLOR_ACCENT,
        ).pack(anchor="w", padx=18, pady=(2, 2))
        ctk.CTkLabel(
            canal_card, text=CANAL_URL,
            font=("Segoe UI", 12), text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w", padx=18, pady=(0, 12))
        ctk.CTkLabel(
            canal_card,
            text="Tutoriais, scripts e ferramentas para automatizar seu estudo.",
            font=FONT_LABEL, text_color=COLOR_TEXT, justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 14))

        botoes = ctk.CTkFrame(canal_card, fg_color="transparent")
        botoes.pack(fill="x", padx=14, pady=(0, 16))
        ctk.CTkButton(
            botoes, text="▶  Abrir canal no YouTube",
            font=FONT_BTN, height=42,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            text_color="#0b1d18", corner_radius=10,
            command=lambda: webbrowser.open(CANAL_URL),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            botoes, text="🔔  Inscrever-se",
            font=FONT_BTN, height=42,
            fg_color="transparent", border_width=1, border_color=COLOR_ACCENT,
            hover_color=COLOR_CARD_HOVER, text_color=COLOR_ACCENT,
            corner_radius=10,
            command=lambda: webbrowser.open(CANAL_URL + "?sub_confirmation=1"),
        ).pack(side="left", padx=4)

        return view

    # -------- Importar TXT --------
    def _importar_txt(self, textbox: ctk.CTkTextbox):
        path = filedialog.askopenfilename(
            title="Selecione um arquivo .txt",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                conteudo = f.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="latin-1") as f:
                conteudo = f.read()
        textbox.delete("1.0", "end")
        textbox.insert("1.0", conteudo)
        self._atualizar_contador()

    def _atualizar_contador(self):
        en = split_sentences(self.txt_en.get("1.0", "end"))
        pt = split_sentences(self.txt_pt.get("1.0", "end"))
        cor = COLOR_ACCENT if len(en) == len(pt) and en else COLOR_TEXT_DIM
        if en and len(en) != len(pt):
            cor = COLOR_DANGER
        self.lbl_contador.configure(
            text=f"EN: {len(en)} frases  •  PT: {len(pt)} frases",
            text_color=cor,
        )

    # -------- Preview de áudio --------
    def _preview(self, idioma: str):
        if idioma == "en":
            frases = split_sentences(self.txt_en.get("1.0", "end"))
            voz = self.config_data["voice_en"]
            fallback = "This is a test of the selected English voice."
        else:
            frases = split_sentences(self.txt_pt.get("1.0", "end"))
            voz = self.config_data["voice_pt"]
            fallback = "Este é um teste da voz selecionada em português."
        texto = frases[0] if frases else fallback
        rate = format_rate(self.config_data["rate"])

        os.makedirs(LOGS_DIR, exist_ok=True)
        # Nome único por clique evita conflito quando pygame ainda
        # está com o arquivo anterior aberto.
        ts = int(datetime.now().timestamp() * 1000)
        out = os.path.join(LOGS_DIR, f"_preview_{idioma}_{ts}.mp3")

        def worker():
            try:
                self._status(f"Gerando prévia ({idioma.upper()})…")
                # Libera qualquer áudio anterior antes de gerar
                try:
                    if pygame.mixer.get_init() is not None:
                        pygame.mixer.music.stop()
                        try:
                            pygame.mixer.music.unload()
                        except Exception:
                            pass
                except Exception:
                    pass
                asyncio.run(self._preview_async(texto, voz, out, rate))
                self._tocar(out)
                self._status("Prévia reproduzida.")
                # Limpa previews antigos da pasta logs/ pra não acumular
                self._limpar_previews_antigos(out)
            except Exception as e:
                log.exception("Falha na prévia")
                self._status(f"Erro na prévia: {e}")
                messagebox.showerror("Prévia", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _limpar_previews_antigos(self, manter: str):
        """Remove arquivos _preview_*.mp3 antigos (mantém só o atual)."""
        try:
            for nome in os.listdir(LOGS_DIR):
                if not nome.startswith("_preview_") or not nome.endswith(".mp3"):
                    continue
                caminho = os.path.join(LOGS_DIR, nome)
                if os.path.abspath(caminho) == os.path.abspath(manter):
                    continue
                try:
                    os.remove(caminho)
                except OSError:
                    pass  # ainda travado pelo pygame, ignora
        except Exception:
            pass

    async def _preview_async(self, texto, voz, out, rate):
        ev = threading.Event()
        await gerar_audio_async(texto, voz, out, rate, ev, max_retries=2)

    def _tocar(self, caminho: str):
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            pygame.mixer.music.stop()
            pygame.mixer.music.load(caminho)
            pygame.mixer.music.play()
        except Exception as e:
            log.warning(f"Falha ao tocar áudio: {e}")
            try:
                os.startfile(caminho)  # fallback Windows
            except Exception:
                pass

    # -------- Pipeline de geração --------
    def _iniciar_geracao(self):
        if self.running:
            return
        nome = self.entry_nome.get().strip()
        texto_en = self.txt_en.get("1.0", "end").strip()
        texto_pt = self.txt_pt.get("1.0", "end").strip()

        if not nome or not texto_en or not texto_pt:
            messagebox.showerror("Erro", "Preencha nome, texto EN e texto PT.")
            return

        frases_en = split_sentences(texto_en)
        frases_pt = split_sentences(texto_pt)
        if len(frases_en) != len(frases_pt):
            messagebox.showerror(
                "Erro",
                f"Número de frases diferente:\n"
                f"EN: {len(frases_en)}  |  PT: {len(frases_pt)}",
            )
            return

        self.cancel_event.clear()
        self.running = True
        self._sem_legenda = bool(self.chk_escuta.get())  # escuta: sem texto EN na frente
        self._tres_vel = True  # 3 velocidades é regra fixa agora
        self._imersao = bool(self.chk_imersao.get())  # imersão: PT escondido, sem áudio PT
        self.btn_gerar.configure(state="disabled")
        self.btn_cancelar.configure(state="normal")

        threading.Thread(
            target=self._pipeline,
            args=(nome, texto_en, texto_pt, frases_en, frases_pt),
            daemon=True,
        ).start()

    def _cancelar(self):
        if not self.running:
            return
        if messagebox.askyesno("Cancelar", "Cancelar a geração em andamento?"):
            self.cancel_event.set()
            self._status("Cancelando…")

    def _pipeline(self, nome_deck, texto_en, texto_pt, frases_en, frases_pt):
        try:
            cfg = self.config_data
            voz_en = cfg["voice_en"]
            voz_pt = cfg["voice_pt"]
            rate = format_rate(cfg["rate"])
            autor = cfg["autor"] or AUTOR

            nome_pasta = safe_name(nome_deck)
            projeto_dir = os.path.join(OUTPUT_DIR, nome_pasta)
            frases_dir = os.path.join(projeto_dir, "frases")
            os.makedirs(frases_dir, exist_ok=True)

            por_frase = 3  # en, pt, mix (a velocidade é no player, não gera lento/rápido)
            total = (len(frases_en) * por_frase) + 2 + 2  # +2 áudios completos +2 (anki+pdf)
            done = 0
            log.info(f"Iniciando projeto '{nome_deck}' ({len(frases_en)} frases)")

            asyncio.run(self._gerar_audios(
                frases_en, frases_pt, frases_dir, projeto_dir,
                texto_en, texto_pt, voz_en, voz_pt, rate, total,
            ))
            done = (len(frases_en) * 3) + 2

            if self.cancel_event.is_set():
                self._status("Cancelado.")
                log.info("Geração cancelada pelo usuário")
                return

            # Anki
            self._set_progress(done, total, "Gerando baralho Anki…")
            apkg_path = self._gerar_anki(
                nome_deck, nome_pasta, projeto_dir, frases_dir,
                frases_en, frases_pt, autor,
            )
            done += 1
            self._set_progress(done, total, "Gerando PDF de roteiro…")

            # PDF
            pdf_path = self._gerar_pdf(
                nome_deck, projeto_dir, frases_en, frases_pt,
                texto_en, texto_pt, autor,
            )
            done += 1

            # v3: salva o projeto na biblioteca + registra o baralho no banco
            try:
                existentes = [x for x in db.listar_projetos() if x["nome"] == nome_deck]
                pid = existentes[0]["id"] if existentes else None
                pid = db.salvar_projeto(
                    nome_deck, texto_en=texto_en, texto_pt=texto_pt,
                    voz_en=voz_en, voz_pt=voz_pt, rate=cfg["rate"], projeto_id=pid,
                )
                db.registrar_baralho(
                    pid, nome_deck, os.path.abspath(apkg_path), len(frases_en),
                )
            except Exception:
                log.exception("Falha ao salvar no banco (nao bloqueia a geracao)")

            self._set_progress(total, total, "Finalizado!")
            log.info(f"Projeto finalizado: {projeto_dir}")
            pasta_abs = os.path.abspath(projeto_dir)
            apkg_nome = os.path.basename(apkg_path)
            pdf_nome = os.path.basename(pdf_path)

            def _concluido():
                abrir = messagebox.askyesno(
                    "Concluído",
                    f"Projeto criado em:\n{pasta_abs}\n\n"
                    f"• Baralho: {apkg_nome}\n"
                    f"• PDF: {pdf_nome}\n\n"
                    "Abrir a pasta agora?",
                )
                if abrir:
                    try:
                        os.startfile(pasta_abs)
                    except Exception:
                        log.exception("Falha ao abrir a pasta do projeto")

            self.after(0, _concluido)
        except asyncio.CancelledError:
            self._status("Cancelado.")
            log.info("Cancelado")
        except Exception as e:
            log.exception("Erro no pipeline")
            self._status(f"Erro: {e}")
            self.after(0, lambda: messagebox.showerror("Erro", str(e)))
        finally:
            self.running = False
            self.after(0, lambda: self.btn_gerar.configure(state="normal"))
            self.after(0, lambda: self.btn_cancelar.configure(state="disabled"))

    async def _gerar_audios(
        self, frases_en, frases_pt, frases_dir, projeto_dir,
        texto_en, texto_pt, voz_en, voz_pt, rate, total,
    ):
        done = 0
        for i, (en, pt) in enumerate(zip(frases_en, frases_pt), start=1):
            if self.cancel_event.is_set():
                raise asyncio.CancelledError()

            await gerar_audio_async(
                en, voz_en, f"{frases_dir}/{i:03}_en.mp3", rate, self.cancel_event,
            )
            done += 1
            self._set_progress(done, total, f"Áudio EN {i}/{len(frases_en)}")

            await gerar_audio_async(
                pt, voz_pt, f"{frases_dir}/{i:03}_pt.mp3", rate, self.cancel_event,
            )
            done += 1
            self._set_progress(done, total, f"Áudio PT {i}/{len(frases_pt)}")

            mix = f"{en}. {pt}"
            await gerar_audio_async(
                mix, voz_en, f"{frases_dir}/{i:03}_mix.mp3", rate, self.cancel_event,
            )
            done += 1
            self._set_progress(done, total, f"Áudio MIX {i}/{len(frases_en)}")
            # Lento/rápido NÃO são mais gerados: a velocidade é controlada no
            # próprio card (playbackRate) a partir do áudio médio.

        await gerar_audio_async(
            texto_en, voz_en, f"{projeto_dir}/texto_completo_en.mp3",
            rate, self.cancel_event,
        )
        done += 1
        self._set_progress(done, total, "Áudio completo EN")

        await gerar_audio_async(
            texto_pt, voz_pt, f"{projeto_dir}/texto_completo_pt.mp3",
            rate, self.cancel_event,
        )
        done += 1
        self._set_progress(done, total, "Áudio completo PT")

    # -------- Anki com cards reversos --------
    def _gerar_anki(
        self, nome_deck, nome_pasta, projeto_dir, frases_dir,
        frases_en, frases_pt, autor,
    ) -> str:
        deck_id = int(hashlib.md5(nome_deck.encode()).hexdigest()[:10], 16)

        css = """
        .card { font-family: Segoe UI, Arial, sans-serif; font-size: 22px;
                text-align: center; color: #e6edf3; background: #0f1419; }
        .pt { color: #2ea88a; font-size: 20px; }
        .autor { color: #8b949e; font-size: 12px; margin-top: 12px; }
        """

        sem_legenda = getattr(self, "_sem_legenda", False)
        imersao = getattr(self, "_imersao", False)
        css += ("\n.players{display:flex;flex-direction:column;align-items:center;gap:8px;margin:10px 0}"
                "\n.auto{font-size:13px;color:#8b949e}"
                "\naudio.spd{width:280px;max-width:92%}"
                "\n.spdrow{display:flex;gap:8px;justify-content:center;flex-wrap:wrap}"
                "\n.spdrow button{font-family:inherit;font-size:14px;cursor:pointer;color:#e6edf3;"
                "background:#1b2430;border:1px solid #2ea88a;border-radius:8px;padding:6px 14px}"
                "\n.spdrow button:hover{background:#2ea88a;color:#0f1419}"
                "\n.spdrow button.on{background:#2ea88a;color:#0f1419}"
                "\n.hint{color:#8b949e;font-size:14px;margin-bottom:12px}"
                "\n.trad{margin-top:14px}.trad summary{cursor:pointer;color:#2ea88a;font-size:14px}"
                "\n.trad .pt{margin-top:8px}\n")

        # Áudio EN: UM player + botões de velocidade que mudam a playbackRate (a
        # "escala"). Usa um arquivo só (o médio); lento/rápido são a mesma gravação
        # tocada mais devagar/rápido. O médio ainda toca sozinho via [sound:]
        # (mecanismo nativo do Anki, garantido). O player HTML5 é pra reouvir na
        # velocidade escolhida.
        players_en = (
            "<div class='players'>"
            "<div class='auto'>▶ médio (toca automático) {{AudioEN}}</div>"
            "<audio class='spd' controls preload='metadata' src='{{ArqEN}}'></audio>"
            "<div class='spdrow'>"
            "<button type='button' onclick='akSpd(this,0.75)'>🐢 lento</button>"
            "<button type='button' onclick='akSpd(this,1)'>▶ normal</button>"
            "<button type='button' onclick='akSpd(this,1.3)'>🐇 rápido</button>"
            "</div></div>"
            "<script>function akSpd(btn,r){var a=document.querySelector('audio.spd');"
            "if(!a)return;a.playbackRate=r;a.currentTime=0;a.play();"
            "var bs=btn.parentElement.getElementsByTagName('button');"
            "for(var i=0;i<bs.length;i++)bs[i].className='';btn.className='on';}</script>"
        )
        fields_def = [
            {"name": "Ingles"},
            {"name": "Portugues"},
            {"name": "AudioEN"},   # [sound:001_en.mp3] -> autoplay médio (nativo)
            {"name": "ArqEN"},     # 001_en.mp3 (nome puro) -> player HTML5 com velocidade
            {"name": "AudioPT"},
            {"name": "Autor"},
        ]
        # 3 velocidades é regra fixa (sempre). Duas flags INDEPENDENTES definem o
        # layout, e se combinam sozinhas:
        #   sem_legenda (🎧): tira o inglês da FRENTE (só áudio); o EN vai pra resposta.
        #   imersao (🌊): oculta o PT numa setinha que expande e remove o áudio PT.
        front_en = "" if sem_legenda else "<br>{{Ingles}}"
        # o inglês só reaparece na resposta quando NÃO estava na frente
        back_en = "{{Ingles}}<br>" if sem_legenda else ""
        if imersao:
            back_pt = ("<details class='trad'><summary>👁 ver tradução (PT)</summary>"
                       "<div class='pt'>{{Portugues}}</div></details>")
        else:
            back_pt = "<div class='pt'>{{Portugues}}</div>{{AudioPT}}"
        hint = ""
        if sem_legenda:  # texto escondido → faz sentido pedir pra ouvir
            emoji = "🎧" + ("🌊" if imersao else "")
            hint = f"<div class='hint'>{emoji} Ouça e tente entender</div>"
        elif imersao:  # texto visível, só sinaliza o modo
            hint = "<div class='hint'>🌊 Imersão</div>"
        variante = (1 if sem_legenda else 0) + (2 if imersao else 0)  # 0..3
        nomes = {
            0: "EN + Áudio v3",
            1: "Escuta v3 (sem texto EN)",
            2: "Imersão v3 (PT oculto, sem áudio PT)",
            3: "Imersão + Escuta v3",
        }
        model = genanki.Model(
            # +20: campos mudaram (player único + velocidade); ID novo pra não
            # conflitar com baralhos já importados do modelo antigo (+10).
            MODEL_ID + 20 + variante, nomes[variante],
            fields=fields_def,
            templates=[{
                "name": "Card",
                "qfmt": hint + players_en + front_en,
                "afmt": "{{FrontSide}}<hr>" + back_en + back_pt
                        + "<div class='autor'>{{Autor}}</div>",
            }],
            css=css,
        )

        deck = genanki.Deck(deck_id, nome_deck)
        media_files = []

        for i, (en, pt) in enumerate(zip(frases_en, frases_pt), start=1):
            note = genanki.Note(
                model=model,
                fields=[
                    en,
                    pt,
                    f"[sound:{i:03}_en.mp3]",   # AudioEN: autoplay médio (nativo)
                    f"{i:03}_en.mp3",           # ArqEN: nome puro p/ o player HTML5
                    f"[sound:{i:03}_pt.mp3]",   # AudioPT
                    autor,
                ],
            )
            deck.add_note(note)
            media_files.extend([
                f"{frases_dir}/{i:03}_en.mp3",
                f"{frases_dir}/{i:03}_pt.mp3",
                f"{frases_dir}/{i:03}_mix.mp3",
            ])

        pacote = genanki.Package(deck)
        pacote.media_files = media_files
        out_path = f"{projeto_dir}/{nome_pasta}.apkg"
        pacote.write_to_file(out_path)
        return out_path

    # -------- PDF --------
    def _gerar_pdf(
        self, nome_deck, projeto_dir, frases_en, frases_pt,
        texto_en, texto_pt, autor,
    ) -> str:
        pdf_path = f"{projeto_dir}/{safe_name(nome_deck)}_roteiro.pdf"
        doc = SimpleDocTemplate(
            pdf_path, pagesize=A4,
            leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
            title=nome_deck, author=autor,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "title", parent=styles["Title"], fontSize=28,
            alignment=TA_CENTER, textColor=colors.HexColor("#2ea88a"),
            spaceAfter=18,
        )
        h1 = ParagraphStyle(
            "h1", parent=styles["Heading1"], fontSize=18,
            textColor=colors.HexColor("#0f1419"), spaceBefore=10, spaceAfter=10,
        )
        h2 = ParagraphStyle(
            "h2", parent=styles["Heading2"], fontSize=13,
            textColor=colors.HexColor("#2ea88a"), spaceBefore=8, spaceAfter=4,
        )
        body = ParagraphStyle(
            "body", parent=styles["BodyText"], fontSize=11, leading=15,
            alignment=TA_LEFT,
        )
        small = ParagraphStyle(
            "small", parent=styles["BodyText"], fontSize=9,
            textColor=colors.HexColor("#666"), alignment=TA_CENTER,
        )

        story = []

        # ---- CAPA ----
        story.append(Spacer(1, 4 * cm))
        story.append(Paragraph(nome_deck, title_style))
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph("Roteiro de Treino", h2))
        story.append(Spacer(1, 6 * cm))
        story.append(Paragraph(f"<b>Autor:</b> {autor}", body))
        story.append(Paragraph(
            f"<b>Data:</b> {datetime.now().strftime('%d/%m/%Y')}", body))
        story.append(Paragraph(
            f"<b>Total de frases:</b> {len(frases_en)}", body))
        story.append(PageBreak())

        # ---- SUMÁRIO ----
        story.append(Paragraph("Sumário", h1))
        story.append(Spacer(1, 0.3 * cm))
        for i, en in enumerate(frases_en, start=1):
            preview = (en[:80] + "…") if len(en) > 80 else en
            story.append(Paragraph(f"<b>{i:03}.</b> {preview}", body))
        story.append(PageBreak())

        # ---- CAP 1: Tabela bilíngue com anotações ----
        story.append(Paragraph("1. Tabela Bilíngue (com anotações)", h1))
        story.append(Paragraph(
            "Inglês à esquerda, português à direita, espaço para anotações.",
            body,
        ))
        story.append(Spacer(1, 0.3 * cm))

        dados = [["#", "Inglês", "Português", "Anotações"]]
        for i, (en, pt) in enumerate(zip(frases_en, frases_pt), start=1):
            dados.append([
                str(i),
                Paragraph(en, body),
                Paragraph(pt, body),
                "",
            ])
        tabela = Table(
            dados,
            colWidths=[0.9 * cm, 6.2 * cm, 6.2 * cm, 3.5 * cm],
            repeatRows=1,
        )
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2ea88a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c8d0d8")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f6f8fa")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(tabela)
        story.append(PageBreak())

        # ---- CAP 2: Numerado para leitura ----
        story.append(Paragraph("2. Roteiro Numerado", h1))
        story.append(Paragraph(
            "Cada frase com inglês em cima, português logo abaixo.",
            body,
        ))
        story.append(Spacer(1, 0.3 * cm))
        for i, (en, pt) in enumerate(zip(frases_en, frases_pt), start=1):
            story.append(Paragraph(f"<b>{i:03}.</b> {en}", body))
            story.append(Paragraph(
                f"<font color='#2ea88a'>{pt}</font>", body))
            story.append(Spacer(1, 0.25 * cm))
        story.append(PageBreak())

        # ---- CAP 3: Textos completos ----
        story.append(Paragraph("3. Texto Completo — Inglês", h1))
        for paragrafo in texto_en.split("\n"):
            if paragrafo.strip():
                story.append(Paragraph(paragrafo, body))
                story.append(Spacer(1, 0.2 * cm))
        story.append(PageBreak())

        story.append(Paragraph("3. Texto Completo — Português", h1))
        for paragrafo in texto_pt.split("\n"):
            if paragrafo.strip():
                story.append(Paragraph(paragrafo, body))
                story.append(Spacer(1, 0.2 * cm))

        story.append(Spacer(1, 1 * cm))
        story.append(Paragraph(f"Gerado por {autor} — Anki + Áudio v2", small))

        doc.build(story)
        return pdf_path

    # -------- atualização de UI thread-safe --------
    def _set_progress(self, done: int, total: int, texto: str):
        pct = done / total if total else 0
        self.after(0, lambda: self.progress.set(pct))
        self.after(0, lambda: self.lbl_status.configure(
            text=f"{texto}  ({int(pct * 100)}%)",
            text_color=COLOR_TEXT,
        ))

    def _status(self, texto: str):
        self.after(0, lambda: self.lbl_status.configure(
            text=texto, text_color=COLOR_TEXT_DIM,
        ))


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    try:
        app = AnkiApp()
        app.mainloop()
    except Exception as e:
        log.exception("Erro fatal")
        raise
