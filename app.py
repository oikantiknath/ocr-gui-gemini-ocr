#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st
from PIL import Image
from PIL import UnidentifiedImageError

# --- Config ---
BASE_DIR = Path(os.environ.get("BASE_DIR", Path(__file__).parent))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", BASE_DIR / "vis-samples"))  # structure: <lang>/<region>/{images,jsons}

st.set_page_config(page_title="IndicDLP Snippet Viewer", layout="wide")

@st.cache_data(show_spinner=False)
def list_languages(base: Path) -> List[str]:
    if not base.exists():
        return []
    return sorted([p.name for p in base.iterdir() if p.is_dir()])

@st.cache_data(show_spinner=False)
def list_regions(base: Path, lang: str) -> List[str]:
    lang_dir = base / lang
    if not lang_dir.exists():
        return []
    return sorted([p.name for p in lang_dir.iterdir() if p.is_dir()])

@st.cache_data(show_spinner=False)
def load_pairs(base: Path, lang: str, region: str) -> List[Tuple[Path, Path]]:
    """Return list of (image_path, json_path) pairs where stems match."""
    region_dir = base / lang / region
    img_dir = region_dir / "images"
    js_dir  = region_dir / "jsons"
    if not img_dir.exists() or not js_dir.exists():
        return []
    pairs = []
    for img in sorted(img_dir.glob("*.png")):
        js = js_dir / f"{img.stem}.json"
        if js.exists():
            pairs.append((img, js))
    return pairs

def parse_annotation(js_path: Path) -> Tuple[Dict[int, str], List[Dict]]:
    """Return (cat_id->name, annotations). Robust to missing keys."""
    with open(js_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cat_map = {c["id"]: c["name"] for c in data.get("categories", []) if "id" in c and "name" in c}
    ann = data.get("annotations", [])
    return cat_map, ann

# --- UI ---
st.title("IndicDLP gemini-OCR GUI")

langs = list_languages(OUTPUT_DIR)
c1, c2 = st.columns(2)
with c1:
    lang = st.selectbox("Language", options=["— select —"] + langs, index=0)
with c2:
    regions = list_regions(OUTPUT_DIR, lang) if lang != "— select —" else []
    region = st.selectbox("Region", options=["— select —"] + regions, index=0)

if lang == "— select —" or region == "— select —":
    st.info("Choose both language and region to view samples.")
    st.stop()

pairs = load_pairs(OUTPUT_DIR, lang, region)
st.caption(f"Found {len(pairs)} samples in `{lang}/{region}`.")

for img_path, js_path in pairs:
    col_img, col_txt = st.columns([1, 1])
    with col_img:
        try:
            st.image(Image.open(img_path), caption=img_path.name, use_column_width=True)
        except UnidentifiedImageError:
            st.error(f"Invalid image file: {img_path.name}")
    with col_txt:
        cat_map, anns = parse_annotation(js_path)
        if not anns:
            st.write(f"**{js_path.name}** — no annotations.")
            continue

        st.write(f"**{js_path.name}**")
        for a in anns:
            cat = cat_map.get(a.get("category_id", -1), f"cat_{a.get('category_id','?')}")
            txt = a.get("text", "").strip()
            # st.markdown(f"- **{cat}**")
            if txt:
                # Preserve line breaks from the JSON text.
                st.code(txt, language=None)
            else:
                st.caption("No text found for this annotation.")
