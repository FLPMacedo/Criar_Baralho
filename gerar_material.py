"""
Gera o PDF "Como Destravar o Inglês — Método + Software AnkiAudio v2"
Material gratuito do canal @UaiScript.

Saída: Material_DestravarIngles.pdf na pasta atual.
Edite as constantes ou as funções de seção para alterar o conteúdo
e rode novamente.
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
TITULO = "Como Destravar o Inglês"
SUBTITULO = "Método de imersão por áudio bilíngue + Anki"
SOFTWARE = "AnkiAudio v2"
ARQUIVO_SAIDA = "Material_DestravarIngles.pdf"
LOGO_PATH = "assets/uaiscript.png"

# Paleta (mesma do app)
COR_PRIMARIA = colors.HexColor("#2ea88a")
COR_PRIMARIA_ESCURA = colors.HexColor("#1c6e5b")
COR_TEXTO = colors.HexColor("#1c2128")
COR_TEXTO_DIM = colors.HexColor("#566573")
COR_FUNDO_CAIXA = colors.HexColor("#eef9f4")
COR_BORDA = colors.HexColor("#c8d0d8")
COR_ALERTA = colors.HexColor("#fff7e6")
COR_ALERTA_BORDA = colors.HexColor("#d9a04a")

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
s_body_left = ParagraphStyle(
    "BodyLeft", parent=s_body, alignment=TA_LEFT,
)
s_lista = ParagraphStyle(
    "Lista", parent=s_body, leftIndent=14, bulletIndent=2, spaceAfter=4,
)
s_small = ParagraphStyle(
    "Small", parent=styles["BodyText"], fontSize=9, leading=12,
    textColor=COR_TEXTO_DIM, alignment=TA_CENTER,
)
s_quote = ParagraphStyle(
    "Quote", parent=s_body, fontSize=12, leading=18, leftIndent=14,
    rightIndent=14, textColor=COR_PRIMARIA_ESCURA,
    fontName="Helvetica-Oblique",
)


# =========================
# HELPERS DE SEÇÃO
# =========================
def p(texto, estilo=s_body):
    return Paragraph(texto, estilo)


def lista_marcador(itens, estilo=s_lista):
    return [
        Paragraph(f"• {item}", estilo) for item in itens
    ]


def lista_numerada(itens, estilo=s_lista):
    return [
        Paragraph(f"<b>{i}.</b> {item}", estilo)
        for i, item in enumerate(itens, start=1)
    ]


def caixa_destaque(titulo, texto, cor_fundo=COR_FUNDO_CAIXA,
                   cor_borda=COR_PRIMARIA):
    """Caixa colorida com título + corpo."""
    inner = [
        Paragraph(f"<b>{titulo}</b>",
                  ParagraphStyle("CaixaT", parent=s_h3,
                                 textColor=cor_borda)),
        Paragraph(texto, s_body_left),
    ]
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


def divisor():
    return HRFlowable(width="100%", thickness=0.5, color=COR_BORDA,
                      spaceBefore=6, spaceAfter=10)


# =========================
# RODAPÉ / NUMERAÇÃO
# =========================
def _pagina(canv, doc):
    canv.saveState()
    canv.setStrokeColor(COR_BORDA)
    canv.setLineWidth(0.3)
    canv.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canv.setFont("Helvetica", 8)
    canv.setFillColor(COR_TEXTO_DIM)
    canv.drawString(2 * cm, 1.1 * cm, f"{TITULO} — {CANAL}")
    canv.drawRightString(
        A4[0] - 2 * cm, 1.1 * cm, f"Página {canv.getPageNumber()}"
    )
    canv.restoreState()


def _pagina_capa(canv, doc):
    # capa não tem rodapé
    pass


# =========================
# SEÇÕES DO CONTEÚDO
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
        f"Material gratuito do canal <b>{CANAL}</b>",
        ParagraphStyle("CapaT", parent=s_body, alignment=TA_CENTER,
                       fontSize=12),
    ))
    story.append(p(
        CANAL_URL,
        ParagraphStyle("CapaUrl", parent=s_body, alignment=TA_CENTER,
                       fontSize=11, textColor=COR_PRIMARIA),
    ))
    story.append(Spacer(1, 5 * cm))
    story.append(p(
        f"Edição {datetime.now().strftime('%B/%Y').capitalize()}  "
        f"•  Distribuição gratuita  •  Proibida a revenda",
        s_small,
    ))
    story.append(PageBreak())


def sec_sumario(story):
    story.append(p("Sumário", s_h1))
    story.append(divisor())
    capitulos = [
        ("Carta aberta", "Por que esse material é grátis"),
        ("Capítulo 1", "Por que você ainda trava no inglês"),
        ("Capítulo 2", "O método: áudio bilíngue + Anki"),
        ("Capítulo 3", "A ferramenta: AnkiAudio v2"),
        ("Capítulo 4", "Como importar e estudar no Anki"),
        ("Capítulo 5", "Cronograma de 30 dias"),
        ("Capítulo 6", "Onde tirar os textos (de graça)"),
        ("Capítulo 7", "Os 7 erros que te mantêm travado"),
        ("Encerramento", "O próximo passo é seu"),
    ]
    dados = [["", c[0], c[1]] for c in capitulos]
    t = Table(dados, colWidths=[0.5 * cm, 3.5 * cm, 12.4 * cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (1, 0), (1, -1), COR_PRIMARIA),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (2, 0), (2, -1), COR_TEXTO),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, COR_BORDA),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.append(t)
    story.append(PageBreak())


def sec_carta(story):
    story.append(p("Carta aberta", s_h1))
    story.append(p("Por que esse material é grátis", s_h2))
    story.append(divisor())
    story.append(p(
        "Esse PDF, junto com o software <b>AnkiAudio v2</b>, foi planejado "
        "originalmente para ser vendido como um mini-curso. O conteúdo, o "
        "método e a ferramenta estão completos."
    ))
    story.append(p(
        "Eu decidi distribuir tudo gratuitamente. O motivo é simples: eu "
        "passei anos travado no inglês. Estudei em escola, fiz curso, "
        "comprei material. E continuei sem conseguir falar uma frase "
        "completa sem trancar. O dia em que eu destravei não foi com um "
        "produto pago — foi quando entendi <i>como o cérebro aprende uma "
        "língua de verdade</i> e parei de seguir o caminho errado."
    ))
    story.append(p(
        "Se esse material destravar uma pessoa que está como eu estava, ele "
        "já cumpriu o objetivo. Não precisa pagar. Precisa <b>aplicar</b>."
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(caixa_destaque(
        "O acordo",
        "Você não precisa pagar nada. Só te peço três coisas: "
        "<b>(1)</b> aplique o método por 30 dias antes de julgar; "
        "<b>(2)</b> se funcionar, marque uma pessoa que precisa disso "
        "no vídeo do canal; <b>(3)</b> não revenda esse PDF nem o software.",
    ))
    story.append(p(f"— {CANAL}", s_quote))
    story.append(PageBreak())


def sec_cap1(story):
    story.append(p("Capítulo 1", s_h2))
    story.append(p("Por que você ainda trava no inglês", s_h1))
    story.append(divisor())
    story.append(p(
        "Se você estuda inglês há mais de um ano e ainda trava na hora de "
        "falar, o problema <b>não é falta de esforço</b> e <b>não é falta "
        "de inteligência</b>. É método. Existem três causas que se repetem "
        "em quase 100% das pessoas que me procuram com essa queixa."
    ))

    story.append(p("Causa 1 — Você consome inglês com os olhos", s_h2))
    story.append(p(
        "Texto escrito, lista de vocabulário, exercício de gramática, filme "
        "com legenda em português. Tudo isso treina <b>leitura</b>. Nenhuma "
        "delas treina o que o seu cérebro precisa: associar <b>som</b> a "
        "<b>significado</b>, sem passar pela letra escrita."
    ))
    story.append(p(
        "Quando alguém fala com você em inglês, você tem milissegundos pra "
        "processar o som. Se seu cérebro precisa converter o som em letra, "
        "depois letra em palavra, depois palavra em tradução, você perde a "
        "frase inteira antes de entender a primeira palavra."
    ))

    story.append(p("Causa 2 — Você estuda palavra solta", s_h2))
    story.append(p(
        "Flashcard com uma palavra e a tradução não funciona. O cérebro "
        "aprende língua em <b>chunks</b> — pedaços de frase com ritmo, "
        "entonação e contexto. <i>“How are you doing?”</i> entra como uma "
        "unidade. As palavras separadas <i>how</i>, <i>are</i>, <i>you</i>, "
        "<i>doing</i> não entram. Por isso quem decora vocabulário sabe "
        "centenas de palavras mas não consegue montar frase."
    ))

    story.append(p("Causa 3 — Você só treina reconhecer, nunca produzir", s_h2))
    story.append(p(
        "Existem dois tipos de habilidade: <b>reconhecimento</b> (você ouve "
        "ou lê e entende) e <b>produção</b> (você precisa gerar a frase do "
        "zero). 99% do que você estuda é reconhecimento. Por isso você "
        "entende vídeo, entende música, entende texto — mas <b>na hora de "
        "falar, trava</b>. Você nunca treinou o caminho reverso: pegar "
        "uma ideia em português e <b>produzir</b> em inglês."
    ))

    story.append(caixa_destaque(
        "Resumo do capítulo",
        "Se você consome inglês só com os olhos, decora palavra solta e "
        "nunca treina produzir do zero, você vai continuar travado por "
        "mais 10 anos — independentemente de quanto tempo estudar."
    ))
    story.append(PageBreak())


def sec_cap2(story):
    story.append(p("Capítulo 2", s_h2))
    story.append(p("O método: áudio bilíngue + Anki", s_h1))
    story.append(divisor())
    story.append(p(
        "O método tem três pilares. Os três resolvem, respectivamente, as "
        "três causas do capítulo anterior."
    ))

    story.append(p("Pilar 1 — Áudio bilíngue (EN, PT, MIX)", s_h2))
    story.append(p(
        "Para cada frase que você quer aprender, são gerados <b>três "
        "áudios</b>:"
    ))
    for item in lista_marcador([
        "<b>Áudio EN</b> — a frase em inglês, voz nativa.",
        "<b>Áudio PT</b> — a tradução em português, voz nativa.",
        "<b>Áudio MIX</b> — a frase em inglês <i>seguida</i> da tradução, "
        "no mesmo arquivo. Esse é o que cria a ponte mental.",
    ]):
        story.append(item)
    story.append(p(
        "Ouvir o áudio MIX repetidas vezes treina seu cérebro a <b>associar "
        "som a significado</b> sem passar pela letra. É exatamente o que "
        "faltava."
    ))

    story.append(p("Pilar 2 — Repetição espaçada com Anki", s_h2))
    story.append(p(
        "O Anki é um aplicativo gratuito de <b>flashcards inteligentes</b>. "
        "Ele calcula automaticamente o intervalo ideal pra você revisar "
        "cada card, baseado em quão fácil ou difícil foi pra você lembrar "
        "da última vez. Resultado: você revisa o mínimo necessário pra "
        "<b>não esquecer</b>, e foca o tempo no que ainda não fixou."
    ))
    story.append(p(
        "É de graça, é open source, funciona no PC, Android e iPhone. "
        "Site oficial: <font color='#2ea88a'>https://apps.ankiweb.net</font>"
    ))

    story.append(p("Pilar 3 — Cards reversos (PT → EN)", s_h2))
    story.append(p(
        "Cada frase gera <b>dois cards</b> no baralho:"
    ))
    for item in lista_numerada([
        "<b>EN → PT</b> — você ouve o áudio em inglês, lê a frase e "
        "responde com o português. Treina <i>reconhecimento</i>.",
        "<b>PT → EN</b> — você lê a frase em português e precisa "
        "<i>produzir</i> a frase em inglês de cabeça. <b>Esse é o card "
        "que destrava a fala.</b>",
    ]):
        story.append(item)
    story.append(p(
        "É o card reverso que faz a diferença. É ele que te força a fazer "
        "o caminho exato que sua boca precisa fazer numa conversa real."
    ))

    story.append(caixa_destaque(
        "A combinação completa",
        "<b>Áudio MIX</b> resolve o input. <b>Anki</b> resolve a memória. "
        "<b>Card reverso</b> resolve a produção. Os três juntos, "
        "diariamente, destravam o inglês. O problema é que montar isso "
        "manualmente leva horas por texto. Por isso existe o AnkiAudio v2."
    ))
    story.append(PageBreak())


def sec_cap3(story):
    story.append(p("Capítulo 3", s_h2))
    story.append(p(f"A ferramenta: {SOFTWARE}", s_h1))
    story.append(divisor())
    story.append(p(
        f"O <b>{SOFTWARE}</b> é o software gratuito que automatiza tudo "
        "do capítulo anterior. Você cola o texto em inglês e em português, "
        "clica em um botão, e ele gera todos os áudios, monta o baralho "
        "Anki com cards reversos e ainda exporta um PDF de roteiro pra "
        "estudo offline."
    ))

    story.append(p("Instalação", s_h2))
    for item in lista_numerada([
        "Baixe o arquivo <b>AnkiAudio_v2.exe</b> no link da descrição "
        "do vídeo.",
        "Salve em uma pasta fácil de achar (ex: <i>Documentos\\AnkiAudio</i>).",
        "Dê dois cliques. Na primeira execução o Windows pode pedir "
        "confirmação — clique em <b>Mais informações → Executar assim "
        "mesmo</b>. É falso positivo do empacotador (PyInstaller), "
        "o código é aberto.",
        "Pronto. Não precisa instalar Python nem nada.",
    ]):
        story.append(item)

    story.append(p("Tela Criar Baralho", s_h2))
    story.append(p(
        "É a tela principal. Tem três áreas:"
    ))
    for item in lista_marcador([
        "<b>Nome do Baralho</b> — o nome que aparecerá no Anki. "
        "Exemplo: <i>Inglês — Notícias Semana 01</i>.",
        "<b>Texto em INGLÊS</b> — cole aqui o texto original. Pode ser "
        "uma notícia, diálogo, trecho de livro. <b>Recomendado: 5 a 20 "
        "frases por lote</b>.",
        "<b>Texto em PORTUGUÊS</b> — a tradução correspondente, "
        "<b>uma frase pra cada frase do inglês</b>, na mesma ordem.",
    ]):
        story.append(item)
    story.append(p(
        "O <b>contador embaixo dos textos</b> mostra quantas frases ele "
        "detectou em cada idioma. Se ficar <b>vermelho</b>, o número é "
        "diferente — corrija antes de gerar."
    ))
    story.append(p(
        "Os botões <b>Importar .txt</b> permitem carregar o texto de um "
        "arquivo, útil pra textos grandes."
    ))
    story.append(p(
        "Os botões <b>🔊 Testar voz</b> geram uma prévia rápida do primeiro "
        "trecho com a voz selecionada — use antes de gerar tudo pra "
        "conferir se a voz está agradável."
    ))

    story.append(p("Tela Configurações", s_h2))
    story.append(p(
        "Aqui você ajusta:"
    ))
    for item in lista_marcador([
        "<b>Voz EN</b> — 10 vozes nativas em inglês (americano, "
        "britânico, australiano).",
        "<b>Voz PT</b> — 10 vozes nativas em português brasileiro.",
        "<b>Velocidade</b> — de -50% (mais devagar) a +50% (mais rápido). "
        "Para iniciantes, recomendo entre -10% e -20%.",
        "<b>Autor</b> — aparece no rodapé dos cards do Anki.",
    ]):
        story.append(item)
    story.append(p(
        "As configurações ficam salvas em <i>config_v2.json</i> — você "
        "não precisa reajustar a cada uso."
    ))

    story.append(p("O que é gerado", s_h2))
    story.append(p(
        "Ao clicar em <b>🚀 Gerar Projeto + Baralho + PDF</b>, o software "
        "cria uma pasta dentro de <i>output/</i> com:"
    ))
    for item in lista_marcador([
        "<b>frases/</b> — uma pasta com três áudios MP3 por frase "
        "(EN, PT, MIX), numerados em sequência.",
        "<b>texto_completo_en.mp3</b> — o texto inglês inteiro como um "
        "áudio único, pra escuta passiva.",
        "<b>texto_completo_pt.mp3</b> — o mesmo em português.",
        "<b>NomeDoBaralho.apkg</b> — o baralho pronto pra importar no "
        "Anki, com áudio e cards reversos.",
        "<b>NomeDoBaralho_roteiro.pdf</b> — PDF com capa, sumário, "
        "tabela bilíngue para anotação, versão numerada e textos "
        "completos pra leitura.",
    ]):
        story.append(item)
    story.append(PageBreak())


def sec_cap4(story):
    story.append(p("Capítulo 4", s_h2))
    story.append(p("Como importar e estudar no Anki", s_h1))
    story.append(divisor())

    story.append(p("Importar o .apkg", s_h2))
    for item in lista_numerada([
        "Baixe e instale o Anki: <i>https://apps.ankiweb.net</i>",
        "Abra o Anki.",
        "Vá em <b>Arquivo → Importar</b> (ou <b>File → Import</b>).",
        "Selecione o arquivo <b>NomeDoBaralho.apkg</b> gerado pelo "
        "AnkiAudio v2.",
        "O Anki vai importar o baralho com os áudios já embutidos. "
        "Ele aparece na lista de baralhos.",
    ]):
        story.append(item)

    story.append(p("Como funciona a revisão diária", s_h2))
    story.append(p(
        "O Anki vai te mostrar todos os cards <b>novos</b> e os cards "
        "<b>em revisão</b> do dia. Para cada card:"
    ))
    for item in lista_marcador([
        "<b>Card EN → PT</b> — o áudio em inglês toca, você vê a frase. "
        "Tenta lembrar a tradução. Clica em <b>Mostrar resposta</b>.",
        "<b>Card PT → EN</b> — você vê a frase em português. <b>Diz a "
        "frase em inglês em voz alta</b>, do jeito que você acha que é. "
        "Só depois clica em mostrar resposta.",
    ]):
        story.append(item)
    story.append(caixa_destaque(
        "Detalhe crítico do card reverso",
        "<b>Fale a frase em voz alta</b> antes de mostrar a resposta. "
        "Isso é o que destrava a fala. Se você só ler em silêncio, o "
        "card reverso vira igual ao normal e perde o efeito.",
        cor_fundo=COR_ALERTA, cor_borda=COR_ALERTA_BORDA,
    ))

    story.append(p("Os 4 botões de avaliação", s_h2))
    for item in lista_marcador([
        "<b>De novo</b> — não consegui lembrar. Volta em poucos minutos.",
        "<b>Difícil</b> — lembrei com esforço grande.",
        "<b>Bom</b> — lembrei normalmente. <b>(É o que você vai usar 90% "
        "do tempo.)</b>",
        "<b>Fácil</b> — lembrei sem esforço nenhum. Reserve pra quando "
        "for óbvio mesmo.",
    ]):
        story.append(item)
    story.append(p(
        "Seja <b>honesto</b>. Se errou, marca <i>De novo</i>. O algoritmo "
        "trabalha pra você só se você for sincero com ele."
    ))

    story.append(p("Configuração recomendada de baralho", s_h2))
    story.append(p(
        "No Anki, vá em <b>⚙ Opções</b> do baralho e ajuste:"
    ))
    for item in lista_marcador([
        "<b>Cards novos por dia</b>: comece com <b>10</b>. Aumenta se "
        "estiver tranquilo, mas não passe de 20 nas primeiras semanas.",
        "<b>Revisões máximas por dia</b>: <b>200</b> (mantém folga).",
        "<b>Ordem</b>: <i>ordem do baralho</i> ou <i>aleatória</i>. "
        "Tanto faz.",
    ]):
        story.append(item)
    story.append(PageBreak())


def sec_cap5(story):
    story.append(p("Capítulo 5", s_h2))
    story.append(p("Cronograma de 30 dias", s_h1))
    story.append(divisor())
    story.append(p(
        "Esse cronograma assume <b>20 a 30 minutos por dia</b> de Anki, "
        "mais <b>1 sessão semanal</b> de 15 a 30 min pra gerar um novo "
        "lote, mais escuta passiva durante o dia (sem tempo mínimo)."
    ))

    semanas = [
        ("Semana 1", "Adaptação", [
            "Gere seu primeiro baralho com 5 a 8 frases curtas.",
            "Importe no Anki. Faça as revisões diárias.",
            "Velocidade do áudio: -20%.",
            "Escute o <i>texto_completo_en.mp3</i> 3x por dia (passivo).",
            "Foco: criar o hábito de abrir o Anki todos os dias.",
        ]),
        ("Semana 2", "Consolidação", [
            "Gere o segundo baralho com 8 a 12 frases.",
            "Mantenha as revisões. Não pule dias.",
            "Velocidade do áudio: -10%.",
            "No card reverso, comece a falar <b>em voz alta</b>.",
            "Foco: começar a sentir o ritmo do inglês.",
        ]),
        ("Semana 3", "Ampliação", [
            "Gere o terceiro baralho com 10 a 15 frases.",
            "Use textos um pouco mais difíceis (notícia curta, "
            "diálogo informal).",
            "Velocidade do áudio: -10% ou normal.",
            "Foco: testar variedade de vozes (americano, britânico).",
        ]),
        ("Semana 4", "Velocidade", [
            "Gere o quarto baralho com 15 a 20 frases.",
            "Escute os áudios MIX em velocidade normal (sem reduzir).",
            "Tente repetir em voz alta junto com o áudio (<b>shadowing</b>).",
            "Foco: começar a falar acompanhando o áudio nativo.",
        ]),
    ]
    for nome, titulo, itens in semanas:
        story.append(p(f"{nome} — {titulo}", s_h2))
        for item in lista_numerada(itens):
            story.append(item)
        story.append(Spacer(1, 0.2 * cm))

    story.append(caixa_destaque(
        "Depois dos 30 dias",
        "Se você cumpriu o cronograma, vai notar três coisas: "
        "<b>(1)</b> seu ouvido pega frases inteiras sem 'traduzir' na cabeça, "
        "<b>(2)</b> você consegue responder perguntas simples sem travar, "
        "<b>(3)</b> a velocidade do nativo deixa de assustar. A partir daí "
        "é só manter o ritmo: <b>1 baralho novo por semana, sempre</b>."
    ))
    story.append(PageBreak())


def sec_cap6(story):
    story.append(p("Capítulo 6", s_h2))
    story.append(p("Onde tirar os textos (de graça)", s_h1))
    story.append(divisor())
    story.append(p(
        "O método precisa de <b>texto bilíngue</b> em formato “frase EN ↔ "
        "frase PT”. Estas são as fontes que eu mais uso:"
    ))

    story.append(p("1. ChatGPT (ou qualquer LLM)", s_h2))
    story.append(p(
        "É a fonte mais flexível. Você dá o tema e o nível, e ele gera "
        "o par bilíngue. Use este prompt:"
    ))
    story.append(caixa_destaque(
        "Prompt pronto pra usar",
        "<i>Gere um diálogo curto em inglês americano sobre [TEMA], com "
        "nível [iniciante / intermediário / avançado], em 10 frases. "
        "Depois forneça a tradução em português, uma frase pra cada, "
        "na mesma ordem. Separe inglês e português em dois blocos.</i>",
        cor_fundo=COR_FUNDO_CAIXA,
    ))

    story.append(p("2. BBC Learning English", s_h2))
    story.append(p(
        "<i>https://www.bbc.co.uk/learningenglish</i> — textos curtos com "
        "áudio nativo, divididos por nível. Você pega o texto em inglês, "
        "traduz no DeepL ou no ChatGPT, e está pronto."
    ))

    story.append(p("3. VOA Learning English", s_h2))
    story.append(p(
        "<i>https://learningenglish.voanews.com</i> — notícias em inglês "
        "simplificado, com áudio e transcrição. Excelente pra nível "
        "intermediário."
    ))

    story.append(p("4. Letras de música", s_h2))
    story.append(p(
        "Pegue a letra original e a tradução em sites como Letras.mus.br. "
        "Funciona muito bem, mas atenção: música tem inversões e licenças "
        "poéticas. Não é o melhor para começar."
    ))

    story.append(p("5. Diálogos de filme/série (com legenda)", s_h2))
    story.append(p(
        "Sites de legenda como <i>opensubtitles.org</i> fornecem o texto "
        "em inglês e em português. Pegue trechos curtos e foque em "
        "diálogos do cotidiano."
    ))

    story.append(caixa_destaque(
        "Dica de ouro",
        "Comece <b>fácil</b>. Texto que você entende 80% só de ler. "
        "Se está difícil demais, o cérebro foca em decifrar e não em "
        "fixar. Suba a dificuldade gradualmente, semana a semana."
    ))
    story.append(PageBreak())


def sec_cap7(story):
    story.append(p("Capítulo 7", s_h2))
    story.append(p("Os 7 erros que te mantêm travado", s_h1))
    story.append(divisor())

    erros = [
        ("Pular um dia 'só hoje'", "O algoritmo do Anki é calibrado pra "
         "revisão diária. Pular um dia gera acúmulo. Acumular gera "
         "frustração. Frustração gera abandono. Esse é o ciclo que mata "
         "99% dos estudantes de inglês. <b>Não pule. Nem que faça só 5 "
         "cards.</b>"),
        ("Querer abraçar o mundo", "Gerar 50 frases num lote, importar "
         "todas, e tentar revisar 100 cards novos no dia seguinte. "
         "Resultado: cansaço, esquecimento, abandono. <b>10 cards novos "
         "por dia é suficiente.</b>"),
        ("Não falar em voz alta no card reverso", "Já avisei no capítulo "
         "4, mas é o erro número 1 dos iniciantes. <b>O card reverso só "
         "funciona se você falar a frase</b>. Se ler em silêncio, vira "
         "igual ao card normal."),
        ("Só estudar gramática", "Gramática é importante, mas é a parte "
         "que <b>menos</b> destrava a fala. Você fala em português sem "
         "saber explicar a regra. Em inglês é igual. Foque no input + "
         "produção. A gramática se acomoda sozinha."),
        ("Mudar de método toda semana", "Ler um post novo no Instagram, "
         "ver um vídeo de polyglot, comprar curso novo. Cada troca "
         "reseta seu progresso. <b>Escolha um método e fique 90 dias "
         "nele</b>. Depois reavalie."),
        ("Pular o áudio MIX", "É o áudio mais 'estranho' de ouvir, mas é "
         "o que cria a ponte EN→PT no automático. <b>Mantenha-o no "
         "estudo passivo.</b> Ouça caminhando, dirigindo, lavando louça."),
        ("Comparar seu progresso com o do outro", "Tem gente que destrava "
         "em 30 dias. Tem gente que demora 6 meses. Depende de quanto "
         "input você teve antes, de quanto tempo coloca por dia, de "
         "fatores que ninguém controla. <b>Compete só com você mesmo "
         "de ontem.</b>"),
    ]
    for i, (titulo, texto) in enumerate(erros, start=1):
        story.append(p(f"Erro {i} — {titulo}", s_h2))
        story.append(p(texto))
    story.append(PageBreak())


def sec_encerramento(story):
    story.append(p("Encerramento", s_h1))
    story.append(p("O próximo passo é seu", s_h2))
    story.append(divisor())
    story.append(p(
        "Você chegou ao fim deste material. Isso já te coloca à frente da "
        "maioria, que baixa e nunca lê."
    ))
    story.append(p(
        "Agora a parte importante: <b>aplicar</b>. Tudo aqui é inútil sem "
        "execução. Se você fechar esse PDF, abrir o Anki amanhã, gerar o "
        "primeiro baralho e fizer 10 cards, você já começou. <b>Essa é a "
        "única coisa que importa.</b>"
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(caixa_destaque(
        "Resumo de 1 página",
        "<b>1.</b> Pegue um texto curto em inglês e a tradução. "
        "<b>2.</b> Cole no AnkiAudio v2 e gere o baralho. "
        "<b>3.</b> Importe no Anki. "
        "<b>4.</b> Revise <b>todos os dias</b>, 20–30 min. "
        "<b>5.</b> Fale <b>em voz alta</b> no card reverso. "
        "<b>6.</b> 1 baralho novo por semana. "
        "<b>7.</b> Não pule, não abrace o mundo, não mude de método. "
        "30 dias. Depois me conta nos comentários."
    ))
    story.append(Spacer(1, 0.8 * cm))
    story.append(p(
        f"Se esse material te ajudou, se inscreve no canal "
        f"<b>{CANAL}</b> — tem ferramenta nova toda semana.",
        ParagraphStyle("CtaP", parent=s_body, alignment=TA_CENTER,
                       fontSize=12),
    ))
    story.append(p(
        CANAL_URL,
        ParagraphStyle("CtaUrl", parent=s_body, alignment=TA_CENTER,
                       fontSize=11, textColor=COR_PRIMARIA),
    ))
    story.append(Spacer(1, 2 * cm))
    story.append(p(
        "Boa sorte. Estuda hoje.", s_quote
    ))
    story.append(p(
        f"— {CANAL}",
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
        title=TITULO, author=CANAL,
        subject="Método para destravar o inglês com Anki + áudio bilíngue",
    )
    story = []
    sec_capa(story)
    sec_sumario(story)
    sec_carta(story)
    sec_cap1(story)
    sec_cap2(story)
    sec_cap3(story)
    sec_cap4(story)
    sec_cap5(story)
    sec_cap6(story)
    sec_cap7(story)
    sec_encerramento(story)
    doc.build(story, onFirstPage=_pagina_capa, onLaterPages=_pagina)
    print(f"PDF gerado: {os.path.abspath(ARQUIVO_SAIDA)}")


if __name__ == "__main__":
    build()
