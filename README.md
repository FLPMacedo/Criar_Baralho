# 🎧 Anki Audio Deck Generator
# 🎧 Gerador de Baralho Anki com Áudio (TTS)

Este projeto é um **gerador automático de baralhos Anki com áudio**, focado no estudo de idiomas (Inglês ↔ Português).

Ele recebe textos em dois idiomas, divide em frases, **agrupa as frases em blocos configuráveis**, gera áudios com Text-to-Speech (TTS) e cria automaticamente um baralho Anki pronto para importação.

---

## 🚀 Funcionalidades

- Interface gráfica simples (Tkinter)
- Entrada de texto em **Inglês** e **Português**
- Divisão automática do texto em frases
- **Agrupamento configurável de frases por áudio/card**
- Geração de áudio:
  - Inglês (EN)
  - Português (PT)
  - Áudio misto (EN → PT)
- Criação automática de baralho Anki (`.apkg`)
- Barra de progresso durante a geração
- Organização automática dos arquivos de saída

---

## 🧠 Por que agrupar frases?

Em vez de criar cartões muito curtos (uma frase por card), o usuário pode definir:

> Quantas frases deseja por áudio/card

Isso permite:
- áudios mais naturais
- melhor fluidez
- aprendizado mais contextualizado
- menos cards excessivamente fragmentados

---

## 🖥️ Requisitos

- **Python 3.9 ou superior**
- Windows (Tkinter já vem instalado)

### 📦 Bibliotecas Python

Instale as dependências com:

```bash
pip install edge-tts genanki
