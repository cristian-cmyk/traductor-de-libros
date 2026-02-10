"""PDF Translator — Translate books and documents using Claude AI."""
import io
import os
import subprocess
import sys
import tempfile

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Detect if running on Streamlit Cloud (vs local macOS/Windows)
IS_CLOUD = (
    os.path.exists("/mount/src")
    or os.getenv("STREAMLIT_SHARING") == "true"
    or os.getenv("STREAMLIT_RUNTIME") == "true"
    or sys.platform == "linux"
)


def _get_api_key() -> str:
    """Resolve API key from multiple sources."""
    # Streamlit secrets (cloud deployment)
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if key:
            return key
    except Exception:
        pass

    # Environment variable / .env file
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if key:
        return key

    if not IS_CLOUD:
        # 1Password CLI (local only)
        try:
            result = subprocess.run(
                ["op", "read", "op://Personal/Anthropic API Key/credential"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip().startswith("sk-ant-"):
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # macOS Keychain (local only)
        try:
            result = subprocess.run(
                ["security", "find-generic-password", "-a", "anthropic",
                 "-s", "pdf-translator", "-w"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return ""


# --- Page Config ---
st.set_page_config(
    page_title="PDF Translator",
    page_icon="📖",
    layout="wide",
)

# --- Resolve API Key ---
API_KEY = _get_api_key()

# Check session state first (user already entered key)
if not API_KEY and "temp_api_key" in st.session_state:
    API_KEY = st.session_state["temp_api_key"]

if not API_KEY:
    st.title("📖 PDF Translator")
    st.markdown("#### Translate books and documents using AI")
    st.markdown("---")

    st.markdown(
        "To get started, you need an **Anthropic API key**. "
        "This key connects the app to Claude, the AI that translates your documents."
    )
    st.markdown(
        "Don't have one? Create it free at "
        "[console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) "
        "(you only need to sign up and add credits)."
    )
    st.info(
        "🔒 Your key is used only to translate and is never stored on any server. "
        "It connects directly from this app to Anthropic's API.",
        icon="🔒",
    )

    key_input = st.text_input(
        "Paste your Anthropic API key",
        type="password",
        placeholder="sk-ant-api03-...",
    )

    if st.button("Start translating", type="primary", use_container_width=True) and key_input:
        st.session_state["temp_api_key"] = key_input
        st.rerun()

    st.stop()

# --- Languages ---
LANGUAGES = {
    "Español": "Spanish (Latin American, neutral)",
    "English": "English",
    "Français": "French",
    "Deutsch": "German",
    "Italiano": "Italian",
    "Português": "Portuguese (Brazilian)",
    "中文": "Chinese (Simplified)",
    "日本語": "Japanese",
    "한국어": "Korean",
    "العربية": "Arabic",
    "Русский": "Russian",
    "हिन्दी": "Hindi",
    "Nederlands": "Dutch",
    "Svenska": "Swedish",
    "Polski": "Polish",
    "Türkçe": "Turkish",
}

MODELS = {
    "Sonnet 4.5 — fast, affordable": "claude-sonnet-4-5-20250929",
    "Opus 4.6 — highest quality": "claude-opus-4-6",
    "Haiku 4.5 — ultra fast, cheapest": "claude-haiku-4-5-20251001",
}

# Pricing per million tokens (USD)
MODEL_PRICING = {
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00, "label": "Sonnet 4.5"},
    "claude-opus-4-6":            {"input": 15.00, "output": 75.00, "label": "Opus 4.6"},
    "claude-haiku-4-5-20251001":  {"input": 0.80, "output": 4.00, "label": "Haiku 4.5"},
}


def estimate_cost(word_count: int, model_id: str) -> dict:
    """Estimate translation cost based on word count and model."""
    pricing = MODEL_PRICING.get(model_id, MODEL_PRICING["claude-sonnet-4-5-20250929"])
    tokens_per_word = 1.3
    overhead = 1.15

    input_tokens = int(word_count * tokens_per_word * overhead)
    output_tokens = int(word_count * tokens_per_word * overhead)

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total = input_cost + output_cost

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total": total,
        "model_label": pricing["label"],
    }


def check_api_credits(api_key: str) -> dict:
    """Verify API key works and has credits."""
    import anthropic

    try:
        client = anthropic.Anthropic(api_key=api_key)
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}],
        )
        return {"valid": True, "has_credits": True, "error": ""}
    except anthropic.AuthenticationError:
        return {"valid": False, "has_credits": False, "error": "Invalid API key"}
    except anthropic.PermissionError:
        return {"valid": True, "has_credits": False, "error": "No credits available"}
    except anthropic.RateLimitError:
        return {"valid": True, "has_credits": False, "error": "No credits or rate limit reached"}
    except Exception as e:
        err = str(e).lower()
        if "credit" in err or "billing" in err or "payment" in err:
            return {"valid": True, "has_credits": False, "error": "No credits available"}
        return {"valid": True, "has_credits": True, "error": f"Unknown error: {e}"}

# --- Sidebar ---
with st.sidebar:
    st.header("Settings")

    source_lang = st.selectbox(
        "Source language",
        options=list(LANGUAGES.keys()),
        index=1,  # English
    )

    target_lang = st.selectbox(
        "Target language",
        options=list(LANGUAGES.keys()),
        index=0,  # Español
    )

    model_choice = st.selectbox(
        "AI Model",
        options=list(MODELS.keys()),
        index=0,
    )

    with st.expander("Advanced options"):
        concurrency = st.slider(
            "Parallel workers",
            min_value=1,
            max_value=15,
            value=8,
            help="More workers = faster translation, but higher simultaneous API usage",
        )

        chunk_size = st.slider(
            "Words per batch",
            min_value=2000,
            max_value=10000,
            value=5000,
            step=1000,
            help="Size of each translation batch",
        )

        extract_images = st.checkbox(
            "Include images from PDF",
            value=True,
            help="Extract diagrams and graphics from the original PDF and include them in the translation",
        )

    st.divider()
    st.caption("🔒 Your API key is used only for this session")
    if st.button("Change API key", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- Main UI ---
st.title("📖 PDF Translator")
st.markdown("Translate complete books and documents using AI.")

uploaded_file = st.file_uploader(
    "Upload your PDF",
    type="pdf",
    help="Supports PDFs of any size. Larger files will take longer.",
)

if uploaded_file:
    pdf_bytes = uploaded_file.getvalue()

    from core.extractor import get_pdf_info
    info = get_pdf_info(io.BytesIO(pdf_bytes))

    # --- Document Info ---
    st.markdown("### Your document")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pages", info["pages"])
    col2.metric("Words", f"{info['word_count']:,}")
    col3.metric("Images", info["image_count"])
    col4.metric("Size", f"{len(pdf_bytes) / 1024:.0f} KB")

    if info.get("title"):
        st.caption(f"**Title:** {info['title']}")
    if info.get("author"):
        st.caption(f"**Author:** {info['author']}")

    # --- Cost Estimation ---
    st.divider()
    model = MODELS[model_choice]
    cost = estimate_cost(info["word_count"], model)

    st.markdown("### Estimated cost")
    st.markdown(
        f"Translating **{info['word_count']:,} words** with **{cost['model_label']}** "
        f"will cost approximately **${cost['total']:.2f} USD**."
    )

    with st.expander("Compare prices across models"):
        for model_name, model_id in MODELS.items():
            c = estimate_cost(info["word_count"], model_id)
            selected = " *(selected)*" if model_id == model else ""
            st.markdown(f"- **{c['model_label']}**: ${c['total']:.2f} USD{selected}")
        st.caption("Prices are estimates based on ~1.3 tokens per word. Actual cost may vary slightly.")

    # --- Credit Check ---
    if "credit_status" not in st.session_state:
        st.session_state["credit_status"] = None

    if st.button("Check available credits"):
        with st.spinner("Checking..."):
            result = check_api_credits(API_KEY)
            st.session_state["credit_status"] = result

    if st.session_state["credit_status"]:
        status = st.session_state["credit_status"]
        if status["valid"] and status["has_credits"]:
            st.success("API key is valid and has credits available")
        elif not status["valid"]:
            st.error(f"{status['error']}. Check your key and try again.")
        else:
            st.error(status["error"])
            st.markdown("[Add credits at Anthropic Console](https://console.anthropic.com/settings/billing)")

    st.divider()

    # --- Translate ---
    if st.button("Translate", type="primary", use_container_width=True):
        from core.extractor import extract_text
        from core.chunker import chunk_text
        from core.translator import translate_sync
        from core.pdf_builder import PDFBuilder
        from core.image_handler import extract_images as extract_imgs

        source = LANGUAGES[source_lang]
        target = LANGUAGES[target_lang]
        model = MODELS[model_choice]

        with st.status("Translating document...", expanded=True) as status:

            # Phase 1: Extract text
            st.write("Extracting text from PDF...")
            progress = st.progress(0)
            pages = extract_text(io.BytesIO(pdf_bytes))
            progress.progress(100)
            st.write(f"   {len(pages)} pages extracted")

            # Phase 2: Chunk
            st.write("Splitting into batches...")
            chunks = chunk_text(pages, target_words=chunk_size)
            st.write(f"   {len(chunks)} batches created")

            # Phase 3: Extract images
            images = []
            if extract_images:
                st.write("Extracting images...")
                images = extract_imgs(io.BytesIO(pdf_bytes))
                st.write(f"   {len(images)} images found")

            # Phase 4: Translate
            st.write(f"Translating ({len(chunks)} batches, {concurrency} parallel workers)...")
            translate_progress = st.progress(0)

            def on_translate_progress(completed, total, chunk_idx):
                pct = int(completed / total * 100)
                translate_progress.progress(pct)

            results = translate_sync(
                chunks=chunks,
                source_lang=source,
                target_lang=target,
                api_key=API_KEY,
                model=model,
                max_concurrent=concurrency,
                on_progress=on_translate_progress,
            )

            # Check for errors
            failed = [r for r in results if not r.success]
            if failed:
                st.warning(f"{len(failed)} batch(es) failed: {failed[0].error}")

            successful = [r for r in results if r.success]
            st.write(f"   {len(successful)}/{len(results)} batches translated")

            # Phase 5: Build PDF
            st.write("Generating PDF...")
            builder = PDFBuilder(
                title=info.get("title", "Translated Document"),
                author=info.get("author", ""),
            )
            builder.add_title_page()

            for result in results:
                if result.success:
                    chunk = chunks[result.chunk_index]
                    chunk_images = [img for img in images
                                    if chunk.start_page <= img.page_num <= chunk.end_page]
                    for img in chunk_images:
                        builder.add_image(img.image_data)

                    builder.render_translated_text(result.translated_text)

            st.write(f"   PDF generated: {builder.page_count} pages")
            status.update(label="Translation complete!", state="complete")

        # Store result
        st.session_state["pdf_result"] = builder.get_bytes()
        st.session_state["pdf_pages"] = builder.page_count
        st.session_state["translations"] = results

# --- Download + Preview ---
if "pdf_result" in st.session_state:
    st.divider()

    col1, col2 = st.columns([1, 1])
    with col1:
        st.download_button(
            label=f"Download translated PDF ({st.session_state['pdf_pages']} pages)",
            data=st.session_state["pdf_result"],
            file_name="translated.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

    with col2:
        if st.button("Start over", use_container_width=True):
            for key in ["pdf_result", "pdf_pages", "translations", "credit_status"]:
                st.session_state.pop(key, None)
            st.rerun()

    # Preview
    st.markdown("### Translation preview")
    results = st.session_state.get("translations", [])
    for r in results:
        if r.success:
            with st.expander(f"Batch {r.chunk_index + 1}"):
                st.text(r.translated_text[:2000])
