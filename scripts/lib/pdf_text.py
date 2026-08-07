"""
Extração de texto "column-aware" dos PDFs do Pokémon Mundo Perfeito.

pdftotext -layout embaralha o texto em páginas de 2-3 colunas (confirmado nas
Fases 0-2: tabelas de Z-Move e de preços de TM saíram com colunas intercaladas).
pdfplumber com posição de palavras (x0/top) permite reconstruir a ordem de
leitura correta: agrupa palavras por coluna (posição x), depois por linha
(posição vertical) dentro de cada coluna, e concatena coluna a coluna.
"""
import pdfplumber


def extract_page_columns(page, n_columns=2):
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
    width = page.width
    col_width = width / n_columns
    columns = [[] for _ in range(n_columns)]
    for w in words:
        col = min(int(w["x0"] // col_width), n_columns - 1)
        columns[col].append(w)

    out_lines = []
    for col_words in columns:
        lines = {}
        for w in col_words:
            key = round(w["top"] / 3)
            lines.setdefault(key, []).append(w)
        for key in sorted(lines.keys()):
            line_words = sorted(lines[key], key=lambda w: w["x0"])
            out_lines.append(" ".join(w["text"] for w in line_words))
    return "\n".join(out_lines)


def extract_range(pdf_path, first_page, last_page, n_columns=2, page_marker=True):
    """first_page/last_page são 1-indexados, inclusive."""
    out = []
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(first_page - 1, last_page):
            page = pdf.pages[i]
            text = extract_page_columns(page, n_columns=n_columns)
            if page_marker:
                out.append(f"\n===PAGE {i + 1}===\n{text}")
            else:
                out.append(text)
    return "\n".join(out)


def strip_noise(text):
    """Remove créditos de arte e números de página soltos, que o pdfplumber
    intercala no meio do fluxo de texto por causa da posição das imagens."""
    lines = text.split("\n")
    cleaned = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line == "":
            i += 1
            continue
        if line.startswith("===PAGE"):
            i += 1
            continue
        if line.isdigit() and len(line) <= 4:
            i += 1
            continue
        if line == "Arte feita por":
            # pula a linha de crédito; a linha seguinte normalmente é só o handle do
            # artista (token único, ex.: "drjhordan"). Mas às vezes o pdfplumber cola o
            # handle no FIM de uma linha de conteúdo real (ex.: "Aqua Tail drjhordan") —
            # nesse caso, descarta apenas o último token e preserva o resto da linha.
            nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if nxt and " " not in nxt:
                i += 2
            elif nxt:
                cleaned.append(nxt.rsplit(" ", 1)[0])
                i += 2
            else:
                i += 1
            continue
        cleaned.append(line)
        i += 1
    return "\n".join(cleaned)
