
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import asyncio
import edge_tts
import genanki
import hashlib
import os
import re

# =========================
# CONFIGURAÇÕES
# =========================
AUTOR = "Canal FLPNews"

VOICE_EN = "en-US-AriaNeural"
VOICE_PT = "pt-BR-FranciscaNeural"
RATE = "-10%"

OUTPUT_DIR = "output"
MODEL_ID = 7894561230

# =========================
# FUNÇÕES AUXILIARES
# =========================
def split_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]

async def gerar_audio(texto, voz, caminho):
    tts = edge_tts.Communicate(texto, voice=voz, rate=RATE)
    await tts.save(caminho)

def atualizar_progresso(done, total, texto):
    percent = int((done / total) * 100)
    progress["value"] = percent
    status_var.set(f"{texto} ({percent}%)")
    janela.update_idletasks()

# =========================
# PIPELINE PRINCIPAL
# =========================
def gerar_tudo():
    nome_deck = entrada_nome.get().strip()
    texto_en = texto_ingles.get("1.0", tk.END).strip()
    texto_pt = texto_portugues.get("1.0", tk.END).strip()

    if not nome_deck or not texto_en or not texto_pt:
        messagebox.showerror("Erro", "Preencha todos os campos.")
        return

    frases_en = split_sentences(texto_en)
    frases_pt = split_sentences(texto_pt)

    if len(frases_en) != len(frases_pt):
        messagebox.showerror(
            "Erro",
            f"Número de frases diferente:\nEN: {len(frases_en)} | PT: {len(frases_pt)}"
        )
        return

    # Nome seguro para pasta
    nome_pasta = re.sub(r'[^a-zA-Z0-9_-]', '', nome_deck.replace(" ", "_"))

    # Pastas do projeto
    projeto_dir = os.path.join(OUTPUT_DIR, nome_pasta)
    frases_dir = os.path.join(projeto_dir, "frases")
    os.makedirs(frases_dir, exist_ok=True)

    async def pipeline():
        total = (len(frases_en) * 3) + 3
        done = 0

        # 🔊 Áudios por frase
        for i, (en, pt) in enumerate(zip(frases_en, frases_pt), start=1):
            # EN
            await gerar_audio(en, VOICE_EN, f"{frases_dir}/{i:03}_en.mp3")
            done += 1
            atualizar_progresso(done, total, f"Áudio EN {i}/{len(frases_en)}")

            # PT
            await gerar_audio(pt, VOICE_PT, f"{frases_dir}/{i:03}_pt.mp3")
            done += 1
            atualizar_progresso(done, total, f"Áudio PT {i}/{len(frases_pt)}")

            # MIX (EN -> PT)
            texto_mix = f"{en}. {pt}"
            await gerar_audio(texto_mix, VOICE_EN, f"{frases_dir}/{i:03}_mix.mp3")
            done += 1
            atualizar_progresso(done, total, f"Áudio MIX {i}/{len(frases_en)}")

        # 🔊 Áudios completos
        await gerar_audio(texto_en, VOICE_EN, f"{projeto_dir}/texto_completo_en.mp3")
        done += 1
        atualizar_progresso(done, total, "Áudio completo EN")

        await gerar_audio(texto_pt, VOICE_PT, f"{projeto_dir}/texto_completo_pt.mp3")
        done += 1
        atualizar_progresso(done, total, "Áudio completo PT")

        # 🃏 Baralho Anki
        deck_id = int(hashlib.md5(nome_deck.encode()).hexdigest()[:10], 16)

        model = genanki.Model(
            MODEL_ID,
            "Audio + Ingles + PT",
            fields=[
                {"name": "Ingles"},
                {"name": "Portugues"},
                {"name": "Audio"},
                {"name": "Autor"},
            ],
            templates=[
                {
                    "name": "Card Principal",
                    "qfmt": "{{Audio}}<br><br>{{Ingles}}",
                    "afmt": "{{FrontSide}}<hr>{{Portugues}}<br><br><small>{{Autor}}</small>",
                }
            ],
        )

        deck = genanki.Deck(deck_id, nome_deck)
        media_files = []

        for i, (en, pt) in enumerate(zip(frases_en, frases_pt), start=1):
            note = genanki.Note(
                model=model,
                fields=[
                    en,
                    pt,
                    f"[sound:{i:03}_en.mp3]",
                    AUTOR,
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
        pacote.write_to_file(f"{projeto_dir}/{nome_pasta}.apkg")

        atualizar_progresso(total, total, "Finalizado 🎉")

    asyncio.run(pipeline())

# =========================
# THREAD
# =========================
def iniciar():
    threading.Thread(target=gerar_tudo).start()

# =========================
# INTERFACE GRÁFICA
# =========================
janela = tk.Tk()
janela.title("Gerador Completo Anki + Áudio")
janela.geometry("900x750")

tk.Label(janela, text="Nome do Baralho:", font=("Arial", 11, "bold")).pack(anchor="w", padx=10)
entrada_nome = tk.Entry(janela, width=80)
entrada_nome.pack(padx=10, pady=5)

tk.Label(janela, text="Texto em INGLÊS:", font=("Arial", 11, "bold")).pack(anchor="w", padx=10)
texto_ingles = tk.Text(janela, height=10, wrap="word")
texto_ingles.pack(fill="both", expand=True, padx=10, pady=5)

tk.Label(janela, text="Texto em PORTUGUÊS:", font=("Arial", 11, "bold")).pack(anchor="w", padx=10)
texto_portugues = tk.Text(janela, height=10, wrap="word")
texto_portugues.pack(fill="both", expand=True, padx=10, pady=5)

progress = ttk.Progressbar(janela, orient="horizontal", length=700, mode="determinate")
progress.pack(pady=10)

status_var = tk.StringVar(value="Aguardando...")
tk.Label(janela, textvariable=status_var).pack()

tk.Button(
    janela,
    text="🚀 Gerar Projeto + Baralho",
    font=("Arial", 12, "bold"),
    bg="#2E8B57",
    fg="white",
    height=2,
    command=iniciar
).pack(pady=20)

janela.mainloop()
