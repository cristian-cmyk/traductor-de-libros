#!/bin/bash
# PDF Translator — Setup Script
# Instala dependencias y configura el entorno

set -e

echo "================================"
echo "  PDF Translator — Setup"
echo "================================"
echo ""

# Check Python
if command -v python3 &> /dev/null; then
    PY=$(command -v python3)
    echo "Python encontrado: $($PY --version)"
else
    echo "ERROR: Python 3 no esta instalado."
    echo "Instalar desde: https://www.python.org/downloads/"
    exit 1
fi

# Install dependencies
echo ""
echo "Instalando dependencias..."
$PY -m pip install -r requirements.txt --quiet

# Check for API key
echo ""
if [ -f .env ]; then
    if grep -q "sk-ant-" .env 2>/dev/null; then
        echo "API key encontrada en .env"
    else
        echo "ATENCION: El archivo .env existe pero no tiene una API key valida."
        echo "Editar .env y pegar tu key: ANTHROPIC_API_KEY=sk-ant-tu-key"
    fi
elif [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "API key encontrada en variable de entorno."
else
    echo "No se encontro API key. Configurar con UNO de estos metodos:"
    echo ""
    echo "  1. Copiar .env.example a .env y editar:"
    echo "     cp .env.example .env"
    echo ""
    echo "  2. Exportar variable de entorno:"
    echo "     export ANTHROPIC_API_KEY=sk-ant-tu-key"
    echo ""
    echo "  Obtener una key en: https://console.anthropic.com/settings/keys"
    echo ""
    cp .env.example .env
    echo "Se creo .env desde .env.example — editar con tu key."
fi

echo ""
echo "================================"
echo "  Setup completo!"
echo "================================"
echo ""
echo "Para ejecutar la app:"
echo "  python3 -m streamlit run app.py"
echo ""
