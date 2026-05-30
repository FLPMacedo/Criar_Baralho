"""
Gera o PDF "Roteiro de Vídeo — Destravar o Inglês" do canal @UaiScript.

Saída: Roteiro_Video.pdf
"""

import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# =========================
# IDENTIDADE
# =========================
CANAL = "@UaiScript"
CANAL_URL = "https://www.youtube.com/@UaiScript"
TITULO = "Roteiro de Vídeo"
SUBTITULO = "Como Destravar o Inglês — Método + Software Grátis"
ARQUIVO_SAIDA = "Roteiro_Video.pdf"
LOGO_PATH = "assets/uaiscript.png"

# Paleta (mesma do app)
COR_PRIMARIA = colors.HexColor("#2ea88a")
COR_PRIMARIA_ESCURA = colors.HexColor("#1c6e5b")
COR_TEXTO = colors.HexColor("#1c2128")
COR_TEXTO_DIM = colors.HexColor("#566573")
COR_FUNDO_CAIXA = colors.HexColor("#eef9f4")
COR_BORDA = colors.HexColor("#c8d0d8")
COR_TEMPO = colors.HexColor("#1c6e5b")
COR_CODE_BG = colors.HexColor("#0f1419")
COR_CODE_FG = colors.HexColor("#e6edf3")

# =========================
# ESTILOS
# =========================
styles = getSampleStyleSheet()

s_titulo_capa = ParagraphStyle(
    "TituloCapa", parent=styles["Title"], fontSize=34, leading=40,
    alignment=TA_CENTER, textColor=COR_PRIMARIA, spaceAfter=10,
)
s_subtitulo_capa = ParagraphStyle(
    "SubtituloCapa", parent=styles["Title"], fontSize=16, leading=22,
    alignment=TA_CENTER, textColor=COR_TEXTO_DIM, spaceAfter=20,
)
s_h1 = ParagraphStyle(
    "H1", parent=styles["Heading1"], fontSize=22, leading=26,
    textColor=COR_PRIMARIA, spaceBefore=8, spaceAfter=10,
)
s_h2 = ParagraphStyle(
    "H2", parent=styles["Heading2"], fontSize=15, leading=20,
    textColor=COR_PRIMARIA_ESCURA, spaceBefore=12, spaceAfter=6,
)
s_h3 = ParagraphStyle(
    "H3", parent=styles["Heading3"], fontSize=12, leading=16,
    textColor=COR_TEXTO, spaceBefore=8, spaceAfter=4,
    fontName="Helvetica-Bold",
)
s_body = ParagraphStyle(
    "Body", parent=styles["BodyText"], fontSize=11, leading=16,
    alignment=TA_JUSTIFY, textColor=COR_TEXTO, spaceAfter=6,
)
s_body_left = ParagraphStyle("BodyLeft", parent=s_body, alignment=TA_LEFT)
s_fala = ParagraphStyle(
    "Fala", parent=s_body_left, fontSize=11.5, leading=17,
    leftIndent=14, rightIndent=4,
)
s_broll = ParagraphStyle(
    "Broll", parent=s_body_left, fontSize=10, leading=14,
    leftIndent=14, textColor=COR_TEXTO_DIM,
    fontName="Helvetica-Oblique",
)
s_tempo = ParagraphStyle(
    "Tempo", parent=styles["Heading2"], fontSize=13, leading=16,
    textColor=COR_TEMPO, spaceBefore=10, spaceAfter=4,
    fontName="Helvetica-Bold",
)
s_lista = ParagraphStyle(
    "Lista", parent=s_body, leftIndent=14, bulletIndent=2, spaceAfter=4,
)
s_code = ParagraphStyle(
    "Code", parent=styles["BodyText"], fontSize=9.5, leading=13,
    fontName="Courier", textColor=COR_CODE_FG,
    leftIndent=8, rightIndent=8, spaceBefore=2, spaceAfter=2,
)
s_small = ParagraphStyle(
    "Small", parent=styles["BodyText"], fontSize=9, leading=12,
    textColor=COR_TEXTO_DIM, alignment=TA_CENTER,
)

# =========================
# HELPERS
# =========================
def p(texto, estilo=s_body):
    return Paragraph(texto, estilo)


def lista_marcador(itens, estilo=s_lista):
    return [Paragraph(f"• {it}", estilo) for it in itens]


def lista_numerada(itens, estilo=s_lista):
    return [
        Paragraph(f"<b>{i}.</b> {it}", estilo)
        for i, it in enumerate(itens, start=1)
    ]


def caixa(titulo, conteudo, cor_fundo=COR_FUNDO_CAIXA,
          cor_borda=COR_PRIMARIA):
    inner = [
        Paragraph(f"<b>{titulo}</b>",
                  ParagraphStyle("CT", parent=s_h3, textColor=cor_borda)),
    ]
    if isinstance(conteudo, list):
        inner += conteudo
    else:
        inner.append(Paragraph(conteudo, s_body_left))
    t = Table([[inner]], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), cor_fundo),
        ("BOX", (0, 0), (-1, -1), 1, cor_borda),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return KeepTogether([t, Spacer(1, 0.3 * cm)])


def code_block(linhas):
    """Bloco de código em fundo escuro — quebra entre páginas quando longo."""
    if isinstance(linhas, list):
        texto = "\n".join(linhas)
    else:
        texto = linhas
    pre_style = ParagraphStyle(
        "PreCode", parent=s_code,
        backColor=COR_CODE_BG,
        borderColor=COR_CODE_BG,
        borderPadding=10,
        borderWidth=0,
        leftIndent=8, rightIndent=8,
        leading=13, fontSize=9.5,
        fontName="Courier",
        textColor=COR_CODE_FG,
        spaceBefore=4, spaceAfter=10,
    )
    return Preformatted(texto, pre_style)


def divisor():
    return HRFlowable(width="100%", thickness=0.5, color=COR_BORDA,
                      spaceBefore=6, spaceAfter=10)


# =========================
# RODAPÉ
# =========================
def _pagina(canv, doc):
    canv.saveState()
    canv.setStrokeColor(COR_BORDA)
    canv.setLineWidth(0.3)
    canv.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canv.setFont("Helvetica", 8)
    canv.setFillColor(COR_TEXTO_DIM)
    canv.drawString(2 * cm, 1.1 * cm, f"Roteiro de Vídeo — {CANAL}")
    canv.drawRightString(
        A4[0] - 2 * cm, 1.1 * cm, f"Página {canv.getPageNumber()}"
    )
    canv.restoreState()


def _pagina_capa(canv, doc):
    pass


# =========================
# CONTEÚDO — DADOS
# =========================
BLOCOS = [
    {
        "num": 1, "tempo": "0:00 – 0:15", "titulo": "HOOK",
        "subtitulo": "Promessa direta, sem rodeios",
        "fala": [
            "Você estuda inglês há anos. Sabe a gramática. Lê texto. Mas trava "
            "na hora de falar. Eu também travava. Hoje eu te entrego — "
            "<b>de graça</b> — o método e a ferramenta que mudaram isso.",
        ],
        "broll": [
            "Você na câmera, expressão direta, corte rápido a cada frase",
            "B-roll: tela do Duolingo passando rápido",
            "B-roll: cards do Anki rodando",
            "Pop-up na tela: \"MÉTODO + SOFTWARE + PDF — TUDO GRÁTIS\"",
        ],
    },
    {
        "num": 2, "tempo": "0:15 – 0:45", "titulo": "APRESENTAÇÃO",
        "subtitulo": "Quem é você e o que o espectador vai receber",
        "fala": [
            "Eu sou do canal <b>UaiScript</b>, e aqui a gente automatiza "
            "estudo, trabalho e produtividade com ferramentas que eu mesmo "
            "programo. Hoje você vai sair desse vídeo com <b>três coisas</b>:",
            "<b>1.</b> O entendimento de <b>por que</b> seu inglês trava",
            "<b>2.</b> Um <b>software gratuito</b> que eu desenvolvi pra resolver isso",
            "<b>3.</b> Um <b>PDF completo</b> com o método e um cronograma de 30 dias",
            "Tudo nos links da descrição. Sem curso pago, sem 'turma fechando "
            "hoje', sem enrolação.",
        ],
        "broll": [
            "Texto na tela: 🎁 Software AnkiAudio v2",
            "Texto na tela: 📄 PDF Como Destravar o Inglês",
            "Texto na tela: 🔗 Links na descrição",
        ],
    },
    {
        "num": 3, "tempo": "0:45 – 2:00", "titulo": "POR QUE VOCÊ TRAVA",
        "subtitulo": "Diagnóstico em três motivos",
        "fala": [
            "Antes da ferramenta, o <b>diagnóstico</b>. Você trava por "
            "<b>três motivos</b>.",
            "<b>Um</b> — você consome inglês com os olhos, não com o ouvido. "
            "O seu cérebro nunca associou o <b>som</b> da palavra ao "
            "significado. Ele só associou a <b>letra</b>.",
            "<b>Dois</b> — você estuda palavra solta. O cérebro não aprende "
            "assim. Ele aprende <b>frase em contexto</b>, com prosódia.",
            "<b>Três</b> — você só treina <b>reconhecer</b>. Mas você nunca "
            "treinou <b>produzir</b> — sair do português e ir pro inglês. "
            "Por isso na hora de falar, trava.",
            "Se você se reconheceu nos três, fica até o final. Esse vídeo é "
            "pra você.",
        ],
        "broll": [
            "Livro de inglês fechando",
            "Tela com lista de vocabulário riscada",
            "Seta animada PT ➡ EN piscando",
        ],
    },
    {
        "num": 4, "tempo": "2:00 – 4:00", "titulo": "O MÉTODO",
        "subtitulo": "Áudio bilíngue + Anki + cards reversos",
        "fala": [
            "O método tem <b>três pilares</b>.",
            "<b>Pilar 1 — input auditivo bilíngue.</b> Você pega um texto "
            "curto, gera o áudio em inglês, o áudio em português, e um "
            "terceiro áudio que toca a frase em inglês seguida da tradução. "
            "Esse terceiro áudio é o <b>áudio MIX</b>. Ele cria a ponte "
            "mental EN → PT no seu cérebro <b>sem</b> você precisar pensar.",
            "<b>Pilar 2 — repetição espaçada com Anki.</b> O Anki mostra "
            "os cards na frequência ideal pro seu cérebro <b>não esquecer</b>. "
            "Você não decora — você <b>fixa</b>.",
            "<b>Pilar 3 — cards reversos.</b> Cada frase vira <b>dois</b> "
            "cards: EN→PT (você ouve e lembra a tradução) e PT→EN (você lê "
            "em português e tem que <b>produzir</b> o inglês). É o card "
            "reverso que destrava a fala.",
            "Esses três pilares juntos resolvem os três problemas. O problema "
            "é que <b>montar isso manualmente</b> dá um trabalho absurdo. "
            "Por isso eu programei o software.",
        ],
        "broll": [
            "Texto na tela: PILAR 1 — ÁUDIO BILÍNGUE",
            "Texto na tela: PILAR 2 — REPETIÇÃO ESPAÇADA (ANKI)",
            "Texto na tela: PILAR 3 — CARDS REVERSOS",
        ],
    },
    {
        "num": 5, "tempo": "4:00 – 7:00", "titulo": "DEMONSTRAÇÃO DO SOFTWARE",
        "subtitulo": "Tela compartilhada — abrir AnkiAudio_v2.exe",
        "fala": [
            "Esse é o <b>AnkiAudio v2</b>. Você baixa o .exe na descrição, "
            "dá dois cliques e abre essa tela. Aqui na lateral eu tenho "
            "<b>Criar Baralho</b>, <b>Bônus</b>, <b>Configurações</b> e "
            "<b>Sobre</b>.",
            "No campo <b>Nome do Baralho</b> coloco: <i>Inglês — Destravando "
            "Lição 01</i>.",
            "Em cima eu colo o texto em inglês. Embaixo, a tradução, uma "
            "frase pra cada. O contador embaixo confirma se bateu — <b>verde</b>: "
            "tudo certo.",
            "Aqui em cima eu posso <b>testar a voz</b>. Em <b>Configurações</b> "
            "eu escolho a voz EN, a voz PT e a velocidade.",
            "Agora é só apertar <b>🚀 Gerar Projeto + Baralho + PDF</b>.",
            "Quando termina, ele cria a pasta com os <b>áudios MP3</b> de "
            "cada frase em três versões (EN, PT, MIX), o <b>baralho .apkg</b> "
            "pronto pra importar no Anki, e um <b>PDF de roteiro</b>.",
            "<b>Importar no Anki</b>: abre o Anki, <b>Arquivo → Importar</b>, "
            "escolhe o .apkg. Pronto. Já tem os cards com áudio e os cards "
            "reversos.",
            "E aqui no <b>módulo Bônus</b> — esse é o diferencial — você "
            "tem dois materiais gratuitos do canal: o PDF do método e o "
            "ebook \"21 Temas Cativantes\" com centenas de ideias prontas. "
            "Baixa direto pelo app.",
        ],
        "broll": [
            "Zoom nos botões importantes (Nome, Textos, Gerar)",
            "Mostrar contador mudando de vermelho pra verde",
            "Acelerar 1.5x as partes de espera",
            "Mostrar a pasta output/ aberta no Explorer",
            "Mostrar Anki abrindo o .apkg e cards rodando",
            "Clicar no botão 🎁 Bônus e mostrar os 2 cards de PDF",
        ],
    },
    {
        "num": 6, "tempo": "7:00 – 8:30", "titulo": "CRONOGRAMA",
        "subtitulo": "Rotina de 20–30 min/dia",
        "fala": [
            "A rotina é de <b>20 a 30 minutos por dia</b>, em três momentos:",
            "<b>Momento 1 — Revisão Anki (10–15 min).</b> De manhã. Abre, "
            "revisa, não pula.",
            "<b>Momento 2 — Escuta passiva (durante o dia).</b> Joga o "
            "<i>texto_completo_en.mp3</i> no celular e escuta no caminho, na "
            "academia, lavando louça.",
            "<b>Momento 3 — Novo lote (1x por semana).</b> Sábado ou domingo, "
            "escolhe um texto novo, gera no software, importa no Anki. "
            "<b>Um texto por semana já é suficiente.</b>",
            "No PDF da descrição tem o <b>cronograma detalhado de 30 dias</b>.",
        ],
        "broll": [
            "Mostrar relógio / cronograma na tela",
            "Tela do Anki sendo aberto de manhã",
            "Pessoa usando fone na rua",
        ],
    },
    {
        "num": 7, "tempo": "8:30 – 10:00", "titulo": "ENTREGA DO MATERIAL",
        "subtitulo": "Software + PDF do método + ebook bônus",
        "fala": [
            "Resumindo o que tá na descrição:",
            "🎁 <b>Software AnkiAudio v2 (.exe)</b> — baixou, deu dois cliques, "
            "abriu. Windows. Sem instalar Python, sem nada.",
            "📄 <b>PDF \"Como Destravar o Inglês\"</b> — método em detalhe, "
            "tutorial do app, cronograma de 30 dias, onde achar textos.",
            "📄 <b>Ebook \"21 Temas Cativantes\"</b> — 21 temas modernos "
            "com centenas de títulos prontos pra virar texto e baralho.",
            "Esse material <b>era pra ser vendido</b>. Eu decidi entregar "
            "<b>de graça</b> porque eu sei o que é estudar inglês durante "
            "anos e continuar travado.",
        ],
        "broll": [
            "Mostrar os 3 links na descrição",
            "Pop-up: 🎁 SOFTWARE + 📄 PDF + 📄 EBOOK",
        ],
    },
    {
        "num": 8, "tempo": "10:00 – 11:00", "titulo": "CTA + ENCERRAMENTO",
        "subtitulo": "Curtida, inscrição, compartilhamento",
        "fala": [
            "Se esse vídeo te ajudou, faz três coisas pra mim:",
            "<b>1.</b> <b>Curte o vídeo</b> — isso faz o YouTube mostrar "
            "pra mais gente travada igual você estava.",
            "<b>2.</b> <b>Se inscreve no canal</b> — eu solto ferramenta "
            "nova toda semana.",
            "<b>3.</b> <b>Marca uma pessoa nos comentários</b> que precisa "
            "destravar o inglês. Manda esse vídeo pra ela.",
            "E se você usar o software e funcionar, <b>volta aqui</b> e me "
            "conta nos comentários. Eu leio todos.",
            "Valeu, e até a próxima.",
        ],
        "broll": [
            "Card final: vídeo recomendado",
            "Botão \"Inscrever-se\" piscando",
            "Logo do canal",
        ],
    },
]

# Texto de demonstração
TEXTO_EN = [
    "I studied English for years, but I still freeze when I have to speak.",
    "The problem is not grammar or vocabulary.",
    "My brain never learned to connect sound to meaning without thinking.",
    "Reading is not the same as listening.",
    "Today, I use audio every single day to fix this.",
    "I listen to the same sentence in English, then in Portuguese, "
    "and then both together.",
    "After thirty days, the words start to feel natural.",
    "The secret is simple: input every day, no exceptions.",
]
TEXTO_PT = [
    "Estudei inglês por anos, mas ainda travo na hora de falar.",
    "O problema não é gramática nem vocabulário.",
    "Meu cérebro nunca aprendeu a conectar som a significado sem pensar.",
    "Ler não é a mesma coisa que ouvir.",
    "Hoje, eu uso áudio todos os dias para resolver isso.",
    "Eu ouço a mesma frase em inglês, depois em português e depois "
    "as duas juntas.",
    "Depois de trinta dias, as palavras começam a parecer naturais.",
    "O segredo é simples: input todos os dias, sem exceção.",
]

# Descrição do YouTube
DESCRICAO_YT = """\
Como destravar o inglês com um software que eu criei.

Mostro nesse vídeo o método que tô usando pra finalmente conectar
som a significado em inglês — imersão por áudio bilíngue + repetição
espaçada no Anki — e o software gratuito que automatiza esse
processo (gera os áudios, monta o baralho com cards reversos e
exporta um PDF de roteiro pra estudo offline).

→ AnkiAudio v2 (software): [link]
→ PDF do método: [link]
→ Anki (oficial): https://apps.ankiweb.net/

Capítulos
00:00 Abertura
00:45 Por que a gente trava
02:00 O método
04:00 Demonstração do software
07:00 Como aplicar na rotina
08:30 Os arquivos pra baixar
10:00 Encerramento

Canal: youtube.com/@UaiScript\
"""

CHECKLIST_GRAVACAO = [
    "Reler o roteiro 2x em voz alta",
    "Ter o texto EN/PT de exemplo pronto pra colar",
    "Anki instalado com tela limpa",
    "AnkiAudio v2 testado e funcionando",
    "PDFs do bônus testados (abrindo no app)",
    "Microfone testado",
    "Iluminação ok",
    "Câmera enquadrada",
    "Fundo limpo e identificável",
    "Telefone no modo silencioso",
]


# =========================
# SEÇÕES
# =========================
def sec_capa(story):
    story.append(Spacer(1, 3 * cm))
    if os.path.exists(LOGO_PATH):
        try:
            img = Image(LOGO_PATH, width=3.5 * cm, height=3.5 * cm)
            img.hAlign = "CENTER"
            story.append(img)
            story.append(Spacer(1, 0.6 * cm))
        except Exception:
            pass
    story.append(p(TITULO, s_titulo_capa))
    story.append(p(SUBTITULO, s_subtitulo_capa))
    story.append(Spacer(1, 1.5 * cm))
    story.append(p(
        f"Documento de gravação — Canal <b>{CANAL}</b>",
        ParagraphStyle("CapaT", parent=s_body, alignment=TA_CENTER,
                       fontSize=12),
    ))
    story.append(p(
        CANAL_URL,
        ParagraphStyle("CapaUrl", parent=s_body, alignment=TA_CENTER,
                       fontSize=11, textColor=COR_PRIMARIA),
    ))
    story.append(Spacer(1, 4 * cm))
    story.append(p(
        f"Edição {datetime.now().strftime('%B/%Y').capitalize()}  "
        f"•  Duração-alvo: 10–12 min  •  Formato: câmera + tela",
        s_small,
    ))
    story.append(PageBreak())


def sec_visao_geral(story):
    story.append(p("Visão geral do vídeo", s_h1))
    story.append(divisor())
    story.append(p(
        "Vídeo dividido em <b>8 blocos cronometrados</b>, com duração-alvo "
        "total entre 10 e 12 minutos. Estrutura clássica de YouTube "
        "para conversão: hook → diagnóstico → método → produto → CTA."
    ))
    story.append(Spacer(1, 0.4 * cm))

    dados = [["Bloco", "Tempo", "Título", "Função"]]
    for b in BLOCOS:
        dados.append([
            f"#{b['num']}",
            b["tempo"],
            b["titulo"],
            b["subtitulo"],
        ])
    t = Table(
        dados,
        colWidths=[1.2 * cm, 2.6 * cm, 4.5 * cm, 8.5 * cm],
        repeatRows=1,
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COR_PRIMARIA),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, COR_BORDA),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f6f8fa")]),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (1, 1), (1, -1), COR_TEMPO),
        ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(PageBreak())


def sec_blocos(story):
    story.append(p("Roteiro bloco a bloco", s_h1))
    story.append(divisor())
    for b in BLOCOS:
        story.append(p(f"⏱ {b['tempo']}", s_tempo))
        story.append(p(f"Bloco {b['num']} — {b['titulo']}", s_h1))
        story.append(p(f"<i>{b['subtitulo']}</i>", s_body_left))
        story.append(Spacer(1, 0.2 * cm))

        story.append(p("Fala", s_h3))
        for linha in b["fala"]:
            story.append(p(linha, s_fala))
        story.append(Spacer(1, 0.2 * cm))

        story.append(p("B-roll / Visual", s_h3))
        for it in b["broll"]:
            story.append(p(f"• {it}", s_broll))
        story.append(Spacer(1, 0.5 * cm))
        story.append(divisor())


def sec_texto_demo(story):
    story.append(PageBreak())
    story.append(p("Texto de demonstração (Bloco 5)", s_h1))
    story.append(divisor())
    story.append(p(
        "Use exatamente este texto na hora de demonstrar o software. "
        "São <b>8 frases curtas, casadas 1:1 EN/PT</b>, sobre o próprio tema "
        "do vídeo. Vai gerar áudios curtos e um baralho rápido — perfeito pra "
        "mostrar o app funcionando sem prender o espectador."
    ))
    story.append(p(
        "<b>Nome do baralho sugerido:</b> "
        "<font color='#2ea88a'>Inglês — Destravando Lição 01</font>",
        s_body_left,
    ))

    story.append(p("🇺🇸 Texto em INGLÊS (cole no campo \"Texto em INGLÊS\")",
                   s_h2))
    story.append(code_block(TEXTO_EN))

    story.append(p("🇧🇷 Texto em PORTUGUÊS (cole no campo \"Texto em "
                   "PORTUGUÊS\")", s_h2))
    story.append(code_block(TEXTO_PT))

    story.append(p("Tabela bilíngue (referência visual)", s_h2))
    dados = [["#", "Inglês", "Português"]]
    for i, (en, pt) in enumerate(zip(TEXTO_EN, TEXTO_PT), start=1):
        dados.append([str(i), Paragraph(en, s_body_left),
                      Paragraph(pt, s_body_left)])
    t = Table(dados, colWidths=[0.9 * cm, 7.7 * cm, 7.8 * cm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COR_PRIMARIA),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, COR_BORDA),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f6f8fa")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)

    story.append(Spacer(1, 0.5 * cm))
    story.append(caixa(
        "Por que esse texto específico",
        [
            Paragraph("• <b>Conta uma história</b> — o espectador se "
                      "identifica enquanto vê o app funcionando.",
                      s_body_left),
            Paragraph("• <b>Reforça o método</b> que você acabou de explicar "
                      "no bloco 4.", s_body_left),
            Paragraph("• <b>8 frases curtas</b> = baralho rápido de gerar "
                      "(~2 minutos de áudio total).", s_body_left),
            Paragraph("• <b>Vocabulário acessível</b> — sem palavra estranha "
                      "que tire o foco do produto.", s_body_left),
        ],
    ))


def sec_descricao_yt(story):
    story.append(PageBreak())
    story.append(p("Descrição do vídeo (YouTube)", s_h1))
    story.append(divisor())
    story.append(p(
        "<b>Cole este texto exatamente como está na descrição do vídeo no "
        "YouTube.</b> Substitua os marcadores entre colchetes "
        "<i>[LINK_SOFTWARE]</i>, <i>[LINK_PDF_METODO]</i> e "
        "<i>[LINK_PDF_TEMAS]</i> pelos links reais (Drive, Mega, Hotmart) "
        "antes de publicar."
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(code_block(DESCRICAO_YT))


def sec_thumbnail_titulo(story):
    story.append(PageBreak())
    story.append(p("Thumbnail e título", s_h1))
    story.append(divisor())

    story.append(p("Sugestões de título", s_h2))
    for it in lista_numerada([
        "Criei um software pra destravar o inglês",
        "O método que tô usando pra destravar o inglês",
        "Anki + áudio bilíngue: o método que tô testando",
    ]):
        story.append(it)

    story.append(p("Elementos da thumbnail", s_h2))
    for it in lista_marcador([
        "Texto curto e direto (3–4 palavras no máximo)",
        "Print do app aparecendo de forma clara",
        "Fundo escuro com acento verde-água #2ea88a (identidade do app)",
        "Sem setinhas vermelhas, sem caras de espanto, sem all-caps",
        "Sua foto opcional — se usar, neutra e centrada",
    ]):
        story.append(it)

    story.append(p("Tags sugeridas", s_h2))
    story.append(p(
        "inglês, anki, destravar inglês, áudio bilíngue, "
        "edge tts, automação estudo, uaiscript"
    ))


def sec_checklist(story):
    story.append(PageBreak())
    story.append(p("Checklist antes de gravar", s_h1))
    story.append(divisor())
    story.append(p(
        "Marque cada item à mão antes de ligar a câmera. "
        "Vídeo bom começa com produção limpa."
    ))
    story.append(Spacer(1, 0.4 * cm))

    dados = [["☐", "Item"]]
    for it in CHECKLIST_GRAVACAO:
        dados.append(["☐", it])
    t = Table(dados, colWidths=[1.2 * cm, 15.2 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COR_PRIMARIA),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("FONTSIZE", (0, 1), (0, -1), 14),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, COR_BORDA),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f6f8fa")]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)

    story.append(Spacer(1, 1.2 * cm))
    story.append(p(
        f"— {CANAL} · {CANAL_URL}",
        ParagraphStyle("Sig", parent=s_small, alignment=TA_CENTER),
    ))


# =========================
# MAIN
# =========================
def build():
    doc = SimpleDocTemplate(
        ARQUIVO_SAIDA, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2.2 * cm,
        title=f"{TITULO} — {SUBTITULO}", author=CANAL,
        subject="Roteiro de produção do vídeo do canal UaiScript",
    )
    story = []
    sec_capa(story)
    sec_visao_geral(story)
    sec_blocos(story)
    sec_texto_demo(story)
    sec_descricao_yt(story)
    sec_thumbnail_titulo(story)
    sec_checklist(story)
    doc.build(story, onFirstPage=_pagina_capa, onLaterPages=_pagina)
    print(f"PDF gerado: {os.path.abspath(ARQUIVO_SAIDA)}")


if __name__ == "__main__":
    build()
