"""Atualização pelo GitHub: a única parte do jogo que usa a internet.

Consulta a última Release de github.com/cauapbritto/joguin (tag vX.Y.Z) e compara com
soulstrike.__version__. Na instalação feita pelo INSTALAR.bat/INSTALAR.sh (pasta com o
código e o .venv) baixa o código da Release e troca os arquivos no lugar; o .venv, os logs
e o progresso salvo (que fica fora da pasta) não são tocados. Se algo der errado no meio,
os arquivos antigos voltam. No executável (.deb em /opt ou .exe) não dá para trocar os
arquivos, então só avisa e abre a página da Release. A cópia do itch.io (o executável com o
loja.json dentro, gerado pelo tools/build_itch.py) abre a página do jogo no itch.io, porque o
app do itch.io é quem atualiza essa cópia.

Só usa a biblioteca padrão e nunca levanta exceção para quem chama: sem internet, o
resultado vem com status "offline".
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__, config

REPO = "cauapbritto/joguin"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
TIMEOUT = 8
MAX_ZIP = 300 * 1024 * 1024

# nunca sobrescritos nem copiados do zip: ambiente do Python, git, logs e sobras de build
KEEP = {".venv", "venv", ".git", "build", "dist", "__pycache__", ".backup_atualizacao"}
KEEP_SUFFIXES = (".log", ".pyc")

# Gravado pelo tools/build_itch.py dentro do executável: {"loja": "itch", "pagina": "https://..."}
STORE_FILE = "loja.json"


@dataclass
class Check:
    status: str                  # "nova", "atual", "sem_release", "offline", "erro"
    latest: str = ""             # "1.2.0"
    notes: str = ""
    zip_url: str = ""
    page_url: str = RELEASES_PAGE
    deb_url: str = ""
    message: str = ""


@dataclass
class Result:
    ok: bool
    message: str
    restart: bool = False
    changed: list = field(default_factory=list)


def parse_version(text):
    """'v1.2.3' -> (1, 2, 3). Partes que não são número viram 0 ('1.2-beta' -> (1, 2, 0))."""
    parts = []
    for piece in str(text).strip().lstrip("vV").split("."):
        digits = ""
        for ch in piece:
            if not ch.isdigit():
                break
            digits += ch
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer(latest, current=__version__):
    return parse_version(latest) > parse_version(current)


def store(root=None):
    """O loja.json do executável do itch.io, ou {} nas outras instalações."""
    try:
        data = json.loads((Path(root or config.ROOT) / STORE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def page_url(root=None):
    """Onde baixar a versão nova: a página do itch.io na cópia de lá, a Release nas outras."""
    return str(store(root).get("pagina") or RELEASES_PAGE)


def install_kind(root=None):
    """'fonte' (pasta do INSTALAR com o código), 'git' (clone de quem programa),
    'itch' (executável baixado do itch.io), 'executavel' (.deb em /opt ou .exe do
    PyInstaller) ou 'somente_leitura'."""
    if store(root).get("loja") == "itch":
        return "itch"
    if getattr(sys, "frozen", False):
        return "executavel"
    root = Path(root or config.ROOT)
    if (root / ".git").exists():
        return "git"
    if not (root / "main.py").is_file() or not os.access(root, os.W_OK):
        return "somente_leitura"
    return "fonte"


def _get(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"SoulStrike/{__version__}",
    })
    return urllib.request.urlopen(req, timeout=timeout)


def check(opener=_get):
    """Pergunta ao GitHub qual é a última versão. Nunca levanta exceção."""
    try:
        with opener(API_LATEST) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return Check("sem_release", message="Nenhuma versão publicada no GitHub ainda.")
        if exc.code in (403, 429):
            return Check("erro", message="O GitHub pediu para esperar um pouco. Tente mais tarde.")
        return Check("erro", message=f"O GitHub respondeu com erro {exc.code}.")
    except (urllib.error.URLError, OSError):
        return Check("offline", message="Sem conexão com a internet.")
    except ValueError:
        return Check("erro", message="Resposta estranha do GitHub.")
    if not isinstance(data, dict) or not data.get("tag_name"):
        return Check("erro", message="Resposta estranha do GitHub.")

    tag = str(data["tag_name"])
    latest = ".".join(str(n) for n in parse_version(tag))
    deb = next((a.get("browser_download_url", "") for a in data.get("assets") or []
                if str(a.get("name", "")).endswith(".deb")), "")
    itch = store().get("pagina")
    info = Check("nova" if is_newer(tag) else "atual", latest=latest,
                 notes=str(data.get("body") or "").strip(),
                 zip_url=str(data.get("zipball_url") or ""),
                 page_url=str(itch or data.get("html_url") or RELEASES_PAGE),
                 deb_url="" if itch else deb)
    info.message = (f"Versão {latest} disponível (você tem a {__version__})." if info.status == "nova"
                    else f"Você já tem a versão mais nova ({__version__}).")
    return info


def _skip(rel):
    parts = rel.parts
    return any(p in KEEP for p in parts) or rel.name.endswith(KEEP_SUFFIXES)


def _source_root(extracted):
    """O zip do GitHub tem uma pasta só por fora (dono-repo-commit/)."""
    if (extracted / "main.py").is_file():
        return extracted
    for child in extracted.iterdir():
        if child.is_dir() and (child / "main.py").is_file() and (child / "soulstrike").is_dir():
            return child
    return None


def _extract(data, dest):
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for member in zf.infolist():
            target = (dest / member.filename).resolve()
            if dest.resolve() not in target.parents and target != dest.resolve():
                raise ValueError("zip com caminho inválido")
        zf.extractall(dest)


def _download(url, opener):
    with opener(url, timeout=60) as resp:
        data = resp.read(MAX_ZIP + 1)
    if len(data) > MAX_ZIP:
        raise ValueError("arquivo grande demais")
    return data


def _install_requirements(root, python=None):
    python = python or sys.executable
    if os.name == "nt" and python.lower().endswith("pythonw.exe"):
        python = python[:-len("pythonw.exe")] + "python.exe"      # pip precisa do console
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    cmd = [python, "-m", "pip", "install", "-r", str(root / "requirements.txt")]
    try:
        done = subprocess.run(cmd, cwd=root, capture_output=True, timeout=600, creationflags=flags)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def apply(info, root=None, opener=_get, pip=_install_requirements):
    """Baixa a Release e troca os arquivos da pasta do jogo. Nunca levanta exceção."""
    root = Path(root or config.ROOT)
    kind = install_kind(root)
    if kind == "git":
        return Result(False, "Esta pasta é um clone do git: atualize com  git pull")
    if kind != "fonte":
        return Result(False, "Esta instalação não se atualiza sozinha: baixe a versão nova na página.")
    if not info.zip_url:
        return Result(False, "A versão nova não tem arquivo para baixar.")

    try:
        data = _download(info.zip_url, opener)
    except (urllib.error.URLError, OSError):
        return Result(False, "A conexão caiu no meio do download. Nada foi alterado.")
    except ValueError:
        return Result(False, "O download veio errado. Nada foi alterado.")

    backup = root / ".backup_atualizacao"
    with tempfile.TemporaryDirectory(prefix="soulstrike-update-") as tmp:
        tmp = Path(tmp)
        try:
            _extract(data, tmp)
        except (zipfile.BadZipFile, ValueError, OSError):
            return Result(False, "O arquivo baixado está corrompido. Nada foi alterado.")
        src = _source_root(tmp)
        if src is None:
            return Result(False, "O arquivo baixado não parece ser do Soul Strike. Nada foi alterado.")

        files = [p for p in src.rglob("*") if p.is_file() and not _skip(p.relative_to(src))]
        old_reqs = _read(root / "requirements.txt")
        written, created = [], []
        shutil.rmtree(backup, ignore_errors=True)
        try:
            for path in files:
                rel = path.relative_to(src)
                dest = root / rel
                if dest.exists():
                    if dest.read_bytes() == path.read_bytes():
                        continue
                    (backup / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest, backup / rel)
                    written.append(rel)
                else:
                    created.append(rel)
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp_dest = dest.with_name(dest.name + ".novo")
                shutil.copy2(path, tmp_dest)
                os.replace(tmp_dest, dest)
            if _read(root / "requirements.txt") != old_reqs and not pip(root):
                raise RuntimeError("pip")
        except (OSError, RuntimeError) as exc:
            _rollback(root, backup, written, created)
            if isinstance(exc, RuntimeError):
                return Result(False, "Não deu para instalar as bibliotecas novas. O jogo voltou como estava.")
            return Result(False, "Não deu para gravar os arquivos. O jogo voltou como estava.")
    shutil.rmtree(backup, ignore_errors=True)
    changed = sorted(str(p) for p in written + created)
    if not changed:
        return Result(True, "Os arquivos já estavam iguais.", changed=changed)
    return Result(True, f"Atualizado para a versão {info.latest}! Reiniciando o jogo.",
                  restart=True, changed=changed)


def _read(path):
    try:
        return path.read_bytes()
    except OSError:
        return None


def _rollback(root, backup, written, created):
    for rel in written:
        try:
            shutil.copy2(backup / rel, root / rel)
        except OSError:
            pass
    for rel in created:
        try:
            (root / rel).unlink()
        except OSError:
            pass
    shutil.rmtree(backup, ignore_errors=True)


def restart():
    """Abre o jogo de novo com os mesmos argumentos (o chamador fecha o atual)."""
    main = Path(config.ROOT) / "main.py"
    try:
        subprocess.Popen([sys.executable, str(main), *sys.argv[1:]], cwd=str(config.ROOT))
        return True
    except OSError:
        return False
