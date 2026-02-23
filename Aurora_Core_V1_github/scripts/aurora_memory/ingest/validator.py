import re

# nomealeatorio_DD_MM_AAAA.txt
FILENAME_PATTERN = re.compile(r".+_\d{2}_\d{2}_\d{4}\.txt")

def validate_file(file_path):
    if not FILENAME_PATTERN.match(file_path.name):
        return False, "Nome de arquivo invalido"

    try:
        content = file_path.read_text(encoding="utf-8").strip()
    except Exception as e:
        return False, f"Erro ao ler arquivo: {e}"

    if len(content) < 10:
        return False, "Conteudo muito curto"

    return True, content
