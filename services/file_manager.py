from pathlib import Path
import time

OUTPUT_DIR = Path("outputs")

def ensure_outdir() -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    return OUTPUT_DIR

def list_output_files():
    """Liệt kê toàn bộ file trong outputs/, mới nhất trước."""
    out_dir = ensure_outdir()
    items = []
    for p in out_dir.iterdir():
        if p.is_file():
            stt = p.stat()
            items.append({
                "path": str(p),
                "suffix": p.suffix.lower(),
                "name": p.name,
                "stem": p.stem,
                "mtime": stt.st_mtime,
                "size": stt.st_size,
                "ts_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stt.st_mtime)),
            })
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items

def next_nonconflict_path(base_stem: str, ext: str) -> str:
    """
    Trả về đường dẫn không trùng, tự tăng _01, _02, ...
    Ví dụ: export_abc.xlsx, export_abc_01.xlsx, export_abc_02.xlsx, ...
    """
    out_dir = ensure_outdir()
    p = out_dir / f"{base_stem}{ext}"
    if not p.exists():
        return str(p)
    i = 2
    while True:
        p2 = out_dir / f"{base_stem}_{i:02d}{ext}"
        if not p2.exists():
            return str(p2)
        i += 1
