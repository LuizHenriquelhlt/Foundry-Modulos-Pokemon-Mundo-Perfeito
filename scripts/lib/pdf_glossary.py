"""
Extração de "glossários" do Livro de Regras (Talentos, Lista de Habilidades Passivas):
páginas em 2 colunas onde cada entrada começa com um título em fonte grande
("...+Digitalt", tamanho >= 12) seguido de um parágrafo em fonte de corpo
("...Calibri", tamanho ~9). Usa a metadata de fonte por caractere do pdfplumber
para separar título de corpo com segurança (mais confiável que heurísticas de
texto puro, já que os nomes de Habilidades/Talentos não formam uma lista fechada
conhecida de antemão).
"""
import pdfplumber


def _page_lines(page, n_columns=1, header_font_substr="Digitalt", header_min_size=11.5):
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False,
                                extra_attrs=["fontname", "size"])
    width = page.width
    col_width = width / n_columns
    columns = [[] for _ in range(n_columns)]
    for w in words:
        col = min(int(w["x0"] // col_width), n_columns - 1)
        columns[col].append(w)

    out = []
    for col_words in columns:
        lines = {}
        for w in col_words:
            key = round(w["top"] / 3)
            lines.setdefault(key, []).append(w)
        for key in sorted(lines.keys()):
            line_words = sorted(lines[key], key=lambda w: w["x0"])
            text = " ".join(w["text"] for w in line_words).strip()
            if not text:
                continue
            is_header = all(
                header_font_substr in w["fontname"] and w["size"] >= header_min_size
                for w in line_words
            )
            out.append((is_header, text))
    return out


def extract_glossary(pdf_path, first_page, last_page, n_columns=1,
                      header_font_substr="Digitalt", header_min_size=11.5):
    """Retorna lista de (titulo, descricao) na ordem em que aparecem no PDF."""
    all_lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(first_page - 1, last_page):
            all_lines.extend(_page_lines(pdf.pages[i], n_columns=n_columns,
                                          header_font_substr=header_font_substr,
                                          header_min_size=header_min_size))

    entries = []
    current_title = None
    current_body = []
    for is_header, text in all_lines:
        if is_header:
            if current_title is not None:
                entries.append((current_title, " ".join(current_body).strip()))
            current_title = text.strip()
            current_body = []
        else:
            if current_title is not None:
                current_body.append(text)
    if current_title is not None:
        entries.append((current_title, " ".join(current_body).strip()))
    return entries
