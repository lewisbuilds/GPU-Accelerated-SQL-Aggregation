from pathlib import Path


def strip_bom(path: Path) -> bool:
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        path.write_bytes(data[3:])
        return True
    return False


def main():
    p = Path("README.md")
    changed = strip_bom(p)
    print("Stripped UTF-8 BOM" if changed else "No BOM present")


if __name__ == "__main__":
    main()
