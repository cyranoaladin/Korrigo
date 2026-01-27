import io
import pathlib
import tokenize


def _iter_grading_py_files() -> list[pathlib.Path]:
    grading_dir = pathlib.Path(__file__).resolve().parents[1]  # backend/grading
    return sorted([p for p in grading_dir.glob("*.py") if p.is_file()])


def _has_forbidden_error_dict_key(source: str) -> bool:
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))

    for i in range(len(tokens) - 1):
        tok = tokens[i]
        nxt = tokens[i + 1]
        if tok.type == tokenize.STRING and tok.string in ("'error'", '"error"'):
            if nxt.type == tokenize.OP and nxt.string == ":":
                return True
    return False


def test_no_error_key_in_grading_code() -> None:
    offenders: list[str] = []
    for path in _iter_grading_py_files():
        source = path.read_text(encoding="utf-8")
        if _has_forbidden_error_dict_key(source):
            offenders.append(str(path))

    assert offenders == [], f"Found forbidden error dict key in: {offenders}"
