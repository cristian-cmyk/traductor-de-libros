"""PDF Translator — Translate books and documents using Claude AI."""
import io
import os
import subprocess
import tempfile

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def _get_api_key() -> str:
    """Resolve API key with priority: env var > .env > 1Password > macOS Keychain > UI input."""

    # 1. Environment variable / .env file
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if key:
        return key

    # 2. 1Password CLI
    try:
        result = subprocess.run(
            ["op", "read", "op://Personal/Anthropic API Key/credential"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip().startswith("sk-ant-"):
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 3. macOS Keychain
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


def save_to_keychain(api_key: str) -> bool:
    """Save API key to macOS Keychain."""
    try:
        # Delete existing entry if any
        subprocess.run(
            ["security", "delete-generic-password", "-a", "anthropic",
             "-s", "pdf-translator"],
            capture_output=True, timeout=5,
        )
        # Add new entry
        result = subprocess.run(
            ["security", "add-generic-password", "-a", "anthropic",
             "-s", "pdf-translator", "-w", api_key],
            capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# --- Page Config ---
st.set_page_config(
    page_title="PDF Translator",
    page_icon="📖",
    layout="wide",
)

# --- Resolve API Key ---
API_KEY = _get_api_key()

if not API_KEY:
    st.warning("No se encontró una API key de Anthropic.")
    st.markdown("**Configurala con cualquiera de estos métodos:**")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔑 Ingresarla ahora",
        "📁 Archivo .env",
        "🔐 1Password",
        "🍎 Keychain macOS",
    ])

    with tab1:
        key_input = st.text_input(
            "Pegá tu API key",
            type="password",
            placeholder="sk-ant-api03-...",
            help="Tu key se usa solo en esta sesión y no se almacena.",
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Usar solo esta vez") and key_input:
                st.session_state["temp_api_key"] = key_input
                st.rerun()
        with col2:
            if st.button("Guardar en Keychain de macOS") and key_input:
                if save_to_keychain(key_input):
                    st.success("Guardada en Keychain. No vas a necesitar ingresarla de nuevo.")
                    st.session_state["temp_api_key"] = key_input
                    st.rerun()
                else:
                    st.error("No se pudo guardar en Keychain.")

    with tab2:
        st.code('echo "ANTHROPIC_API_KEY=sk-ant-tu-key" > ~/pdf-translator/.env', language="bash")
        st.caption("Después reiniciá la app.")

    with tab3:
        st.markdown("""
        Si tenés **1Password CLI** instalado (`op`), guardá tu key como:
        - **Vault:** Personal
        - **Item name:** Anthropic API Key
        - **Field:** credential

        La app la detecta automáticamente.
        """)
        st.code("op item create --category=login --title='Anthropic API Key' 'credential=sk-ant-tu-key'", language="bash")

    with tab4:
        st.markdown("Guardala en el Keychain de macOS desde la terminal:")
        st.code('security add-generic-password -a "anthropic" -s "pdf-translator" -w "sk-ant-tu-key"', language="bash")
        st.caption("La app la detecta automáticamente al reiniciar.")

    # Check if user entered a temp key via UI
    if "temp_api_key" in st.session_state:
        API_KEY = st.session_state["temp_api_key"]
    else:
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
    "Claude Sonnet 4.5 (rápido, económico)": "claude-sonnet-4-5-20250929",
    "Claude Opus 4.6 (máxima calidad)": "claude-opus-4-6",
    "Claude Haiku 4.5 (ultra rápido)": "claude-haiku-4-5-20251001",
}

# Pricing per million tokens (USD) — input / output
MODEL_PRICING = {
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00, "label": "Sonnet 4.5"},
    "claude-opus-4-6":            {"input": 15.00, "output": 75.00, "label": "Opus 4.6"},
    "claude-haiku-4-5-20251001":  {"input": 0.80, "output": 4.00, "label": "Haiku 4.5"},
}


def estimate_cost(word_count: int, model_id: str) -> dict:
    """Estimate translation cost based on word count and model.

    Assumptions:
    - ~1.3 tokens per word (average for multilingual text)
    - Output tokens ≈ input tokens (translation produces similar length)
    - Adds 15% overhead for system prompt and formatting
    """
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
    """Verify API key works and has credits by making a minimal test call.

    Returns dict with:
      - valid: bool (key is valid)
      - has_credits: bool (account has credits)
      - error: str (error message if any)
    """
    import anthropic

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}],
        )
        return {"valid": True, "has_credits": True, "error": ""}
    except anthropic.AuthenticationError:
        return {"valid": False, "has_credits": False, "error": "API key inválida"}
    except anthropic.PermissionError:
        return {"valid": True, "has_credits": False, "error": "Sin créditos disponibles"}
    except anthropic.RateLimitError:
        return {"valid": True, "has_credits": False, "error": "Sin créditos o límite de uso alcanzado"}
    except Exception as e:
        err = str(e).lower()
        if "credit" in err or "billing" in err or "payment" in err:
            return {"valid": True, "has_credits": False, "error": "Sin créditos disponibles"}
        return {"valid": True, "has_credits": True, "error": f"Error desconocido: {e}"}

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Configuración")

    source_lang = st.selectbox(
        "Idioma origen",
        options=list(LANGUAGES.keys()),
        index=1,  # English
    )

    target_lang = st.selectbox(
        "Idioma destino",
        options=list(LANGUAGES.keys()),
        index=0,  # Español
    )

    model_choice = st.selectbox(
        "Modelo Claude",
        options=list(MODELS.keys()),
        index=0,
    )

    concurrency = st.slider(
        "Agentes paralelos",
        min_value=1,
        max_value=15,
        value=8,
        help="Más agentes = más rápido, pero más uso de API simultáneo",
    )

    chunk_size = st.slider(
        "Palabras por lote",
        min_value=2000,
        max_value=10000,
        value=5000,
        step=1000,
        help="Tamaño de cada lote de traducción",
    )

    extract_images = st.checkbox(
        "Extraer e insertar imágenes",
        value=True,
        help="Extrae diagramas/gráficos del PDF original e insértalos en la traducción",
    )

    st.divider()
    source = "1Password" if not os.getenv("ANTHROPIC_API_KEY") and API_KEY else \
             "Keychain" if not os.getenv("ANTHROPIC_API_KEY") else ".env"
    if "temp_api_key" in st.session_state:
        source = "sesión temporal"
    st.caption(f"🔒 API key cargada desde: **{source}**")

# --- Main UI ---
st.title("📖 PDF Translator")
st.markdown("Traducí libros y documentos completos usando inteligencia artificial.")

uploaded_file = st.file_uploader(
    "Subí tu archivo PDF",
    type="pdf",
    help="Soporta PDFs de cualquier tamaño. Los más grandes tardarán más.",
)

if uploaded_file:
    # Show PDF info
    pdf_bytes = uploaded_file.getvalue()

    from core.extractor import get_pdf_info
    info = get_pdf_info(io.BytesIO(pdf_bytes))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Páginas", info["pages"])
    col2.metric("Palabras", f"{info['word_count']:,}")
    col3.metric("Imágenes", info["image_count"])
    col4.metric("Tamaño", f"{len(pdf_bytes) / 1024:.0f} KB")

    if info.get("title"):
        st.caption(f"**Título:** {info['title']}")
    if info.get("author"):
        st.caption(f"**Autor:** {info['author']}")

    # --- Cost Estimation ---
    st.divider()
    model = MODELS[model_choice]
    cost = estimate_cost(info["word_count"], model)

    st.subheader("💰 Costo estimado")
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Tokens entrada", f"{cost['input_tokens']:,}")
    cc2.metric("Tokens salida", f"~{cost['output_tokens']:,}")
    cc3.metric("Costo estimado", f"${cost['total']:.2f} USD")

    # Show comparison across models
    with st.expander("Comparar costo entre modelos"):
        for model_name, model_id in MODELS.items():
            c = estimate_cost(info["word_count"], model_id)
            marker = " ← seleccionado" if model_id == model else ""
            st.markdown(f"- **{c['model_label']}**: ${c['total']:.2f} USD{marker}")

    # --- Credit Check ---
    if "credit_status" not in st.session_state:
        st.session_state["credit_status"] = None

    if st.button("🔍 Verificar créditos disponibles"):
        with st.spinner("Verificando..."):
            result = check_api_credits(API_KEY)
            st.session_state["credit_status"] = result

    if st.session_state["credit_status"]:
        status = st.session_state["credit_status"]
        if status["valid"] and status["has_credits"]:
            st.success("✅ API key válida y con créditos disponibles")
        elif not status["valid"]:
            st.error(f"❌ {status['error']}")
        else:
            st.error(f"❌ {status['error']}")
            st.markdown("[Cargar créditos en Anthropic Console](https://console.anthropic.com/settings/billing)")

    st.divider()

    # Translate button
    if st.button("🚀 Traducir", type="primary", use_container_width=True):
        from core.extractor import extract_text
        from core.chunker import chunk_text
        from core.translator import translate_sync
        from core.pdf_builder import PDFBuilder
        from core.image_handler import extract_images as extract_imgs

        source = LANGUAGES[source_lang]
        target = LANGUAGES[target_lang]
        model = MODELS[model_choice]

        with st.status("Traduciendo documento...", expanded=True) as status:

            # Phase 1: Extract text
            st.write("📄 Extrayendo texto del PDF...")
            progress = st.progress(0)
            pages = extract_text(io.BytesIO(pdf_bytes))
            progress.progress(100)
            st.write(f"   ✅ {len(pages)} páginas extraídas")

            # Phase 2: Chunk
            st.write("✂️ Dividiendo en lotes...")
            chunks = chunk_text(pages, target_words=chunk_size)
            st.write(f"   ✅ {len(chunks)} lotes creados")

            # Phase 3: Extract images
            images = []
            if extract_images:
                st.write("🖼️ Extrayendo imágenes...")
                images = extract_imgs(io.BytesIO(pdf_bytes))
                st.write(f"   ✅ {len(images)} imágenes encontradas")

            # Phase 4: Translate
            st.write(f"🌐 Traduciendo ({len(chunks)} lotes con {concurrency} agentes paralelos)...")
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
                st.warning(f"⚠️ {len(failed)} lotes fallaron: {failed[0].error}")

            successful = [r for r in results if r.success]
            st.write(f"   ✅ {len(successful)}/{len(results)} lotes traducidos")

            # Phase 5: Build PDF
            st.write("📕 Generando PDF...")
            builder = PDFBuilder(
                title=info.get("title", "Translated Document"),
                author=info.get("author", ""),
            )
            builder.add_title_page()

            for result in results:
                if result.success:
                    # Insert images from the corresponding page range
                    chunk = chunks[result.chunk_index]
                    chunk_images = [img for img in images
                                    if chunk.start_page <= img.page_num <= chunk.end_page]
                    for img in chunk_images:
                        builder.add_image(img.image_data)

                    builder.render_translated_text(result.translated_text)

            st.write(f"   ✅ PDF generado: {builder.page_count} páginas")
            status.update(label="✅ Traducción completa!", state="complete")

        # Store result in session state
        st.session_state["pdf_result"] = builder.get_bytes()
        st.session_state["pdf_pages"] = builder.page_count
        st.session_state["translations"] = results

# --- Download + Preview ---
if "pdf_result" in st.session_state:
    st.divider()

    col1, col2 = st.columns([1, 1])
    with col1:
        st.download_button(
            label=f"⬇️ Descargar PDF traducido ({st.session_state['pdf_pages']} páginas)",
            data=st.session_state["pdf_result"],
            file_name="translated.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

    with col2:
        if st.button("🗑️ Limpiar todo", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Preview
    st.subheader("Vista previa de la traducción")
    results = st.session_state.get("translations", [])
    for r in results:
        if r.success:
            preview = r.translated_text[:300] + "..." if len(r.translated_text) > 300 else r.translated_text
            with st.expander(f"Lote {r.chunk_index + 1}"):
                st.text(r.translated_text[:2000])
