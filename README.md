# AnkiAudio v2

Gerador de baralhos Anki com áudio bilíngue (inglês ↔ português).

Cole dois textos correspondentes, escolha as vozes, e o app gera:
- áudios **EN**, **PT** e **MIX** (inglês seguido da tradução) para cada frase
- baralho `.apkg` com **cards reversos** (EN→PT e PT→EN)
- PDF de roteiro com tabela bilíngue para estudo offline

---

**Canal:** [youtube.com/@UaiScript](https://www.youtube.com/@UaiScript) — ferramentas e automações de estudo

---

## Por que existe

Estudar inglês com input apenas visual (ler texto, fazer exercício de gramática) não destrava a fala. O método que esse app automatiza é simples:

- **input auditivo bilíngue** — você ouve a mesma frase em EN, PT e EN→PT
- **repetição espaçada** — via Anki, com cards reversos pra forçar produção
- **um lote por semana** — texto novo virando baralho em minutos

O método completo, com cronograma de 30 dias e dicas de onde tirar textos, está no PDF [Material_DestravarIngles.pdf](assets/bonus/Material_DestravarIngles.pdf).

## Funcionalidades

- UI escura com sidebar (CustomTkinter)
- 19 vozes EN (US, UK, AU) + 3 vozes PT-BR via Edge TTS (gratuito)
- Slider de velocidade de fala (-50% a +50%)
- Preview automático ao trocar de voz nas configurações
- Botão de cancelar geração no meio do processo
- Importar texto a partir de arquivo `.txt`
- Cards reversos no baralho gerado (EN→PT e PT→EN)
- PDF de roteiro com capa, sumário, tabela bilíngue e textos completos
- Módulo **🎁 Bônus** com PDFs embutidos no próprio app
- Logs em `logs/v2.log` e retry automático em falha de rede do TTS

## Instalação

### Opção 1 — Executável Windows (recomendado)

Baixe `AnkiAudio_v2.exe` na aba [Releases](https://github.com/FLPMacedo/Criar_Baralho/releases) e dê dois cliques. Não precisa instalar Python.

> Na primeira execução o Windows pode mostrar "Mais informações → Executar assim mesmo" — é falso positivo do PyInstaller. Código aberto neste repositório.

### Opção 2 — Rodar do código-fonte

```bash
git clone https://github.com/FLPMacedo/Criar_Baralho.git
cd Criar_Baralho
pip install -r requirements.txt
python Criar_BaralhoComAudios_v2.py
```

### Gerar o próprio executável

```bash
pip install pyinstaller
pyinstaller AnkiAudio_v2.spec
```

Saída em `dist/AnkiAudio_v2.exe`.

## Estrutura do projeto

```
Criar_BaralhoComAudios_v2.py    app principal
AnkiAudio_v2.spec               configuração do PyInstaller
requirements.txt                dependências
assets/
  uaiscript.ico                 ícone do app
  uaiscript.png                 avatar do canal
  bonus/                        PDFs embutidos no app (aba 🎁 Bônus)
```

## Materiais incluídos

Dois PDFs do canal, distribuição livre:

- **Como Destravar o Inglês** — método de imersão por áudio + cronograma de 30 dias
- **21 Temas Cativantes para Criar Textos e Flashcards no Anki** — ebook com 21 temas (rotina, esportes, viagens, finanças, música, fé, e mais) e centenas de títulos prontos para virar texto bilíngue

Ambos estão na pasta [assets/bonus/](assets/bonus/) e também aparecem como botões dentro do app, na aba **🎁 Bônus**.

## Stack

- Python 3.12
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — UI
- [edge-tts](https://github.com/rany2/edge-tts) — síntese de voz da Microsoft Edge
- [genanki](https://github.com/kerrickstaley/genanki) — geração de `.apkg`
- [reportlab](https://www.reportlab.com/) — PDFs
- pygame.mixer — preview de áudio
- PyInstaller — empacotamento

## Canal

Tutoriais, scripts e ferramentas para automatizar estudo, trabalho e produtividade.

[**▶ youtube.com/@UaiScript**](https://www.youtube.com/@UaiScript)
