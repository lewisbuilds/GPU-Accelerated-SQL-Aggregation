from pathlib import Path


def main():
    p = Path("README.md")
    raw = p.read_bytes()
    if raw.startswith(b"\xff\xfe"):
        text = raw.decode("utf-16-le")
        p.write_text(text, encoding="utf-8", newline="\n")
        print("Converted README from UTF-16 LE BOM to UTF-8")
    elif raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16-be")
        p.write_text(text, encoding="utf-8", newline="\n")
        print("Converted README from UTF-16 BE BOM to UTF-8")
    else:
        print("README already UTF-8 (no conversion performed)")


if __name__ == "__main__":
    main()
