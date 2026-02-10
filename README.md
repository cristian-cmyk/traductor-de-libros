# PDF Translator

Traduce libros y documentos PDF completos usando inteligencia artificial (Claude de Anthropic).

## Funcionalidades

- Traduce PDFs de cualquier tamaño a 16 idiomas
- Extrae e inserta las imagenes/diagramas del PDF original
- Traduccion paralela con multiples agentes simultaneos (configurable)
- Estimacion de costo antes de traducir
- Verificacion de creditos disponibles
- Genera PDF con formato de libro (portada, capitulos, indice, tipografia Unicode)
- Soporta PDFs con fonts corruptos o custom (doble motor de extraccion)

## Idiomas soportados

Espanol, English, Francais, Deutsch, Italiano, Portugues, Chino, Japones, Coreano, Arabe, Ruso, Hindi, Holandes, Sueco, Polaco, Turco.

## Requisitos

- Python 3.9 o superior
- Una API key de Anthropic ([obtener aqui](https://console.anthropic.com/settings/keys))
- macOS, Linux o Windows

## Instalacion rapida

```bash
# 1. Clonar o descomprimir el proyecto
cd pdf-translator

# 2. Instalar dependencias
pip3 install -r requirements.txt

# 3. Configurar tu API key (elegir UNO de estos metodos):

# Opcion A: Archivo .env (mas simple)
cp .env.example .env
# Editar .env y pegar tu key: ANTHROPIC_API_KEY=sk-ant-tu-key

# Opcion B: Variable de entorno
export ANTHROPIC_API_KEY=sk-ant-tu-key

# Opcion C: macOS Keychain
security add-generic-password -a "anthropic" -s "pdf-translator" -w "sk-ant-tu-key"

# Opcion D: 1Password CLI
op item create --category=login --title='Anthropic API Key' 'credential=sk-ant-tu-key'

# 4. Ejecutar la app
python3 -m streamlit run app.py
```

La app se abre en `http://localhost:8501`.

## Uso

1. Abrir la app en el navegador
2. Subir un PDF con el boton "Subi tu archivo PDF"
3. En la barra lateral, elegir idioma origen, idioma destino y modelo
4. Revisar la estimacion de costo
5. (Opcional) Verificar creditos disponibles
6. Click en "Traducir"
7. Descargar el PDF traducido

## Configuracion

En la barra lateral podes ajustar:

| Opcion | Default | Descripcion |
|--------|---------|-------------|
| Idioma origen | English | Idioma del PDF original |
| Idioma destino | Espanol | Idioma al que traducir |
| Modelo | Sonnet 4.5 | Balance entre calidad y costo |
| Agentes paralelos | 8 | Mas agentes = mas rapido |
| Palabras por lote | 5000 | Tamano de cada lote de traduccion |
| Extraer imagenes | Si | Incluir imagenes del PDF original |

## Modelos disponibles

| Modelo | Costo estimado (100K palabras) | Velocidad |
|--------|-------------------------------|-----------|
| Haiku 4.5 | ~$0.72 USD | Ultra rapido |
| Sonnet 4.5 | ~$2.69 USD | Rapido |
| Opus 4.6 | ~$13.46 USD | Maxima calidad |

## Estructura del proyecto

```
pdf-translator/
├── app.py                 # Interfaz Streamlit
├── core/
│   ├── extractor.py       # Extraccion de texto (PyMuPDF + PyPDF2)
│   ├── chunker.py         # Division en lotes respetando capitulos
│   ├── translator.py      # Traduccion paralela con Claude API
│   ├── pdf_builder.py     # Generacion de PDF con formato libro
│   └── image_handler.py   # Extraccion de imagenes del PDF
├── fonts/                 # Fuentes DejaVu (Unicode completo)
├── .env.example           # Template de configuracion
├── requirements.txt       # Dependencias Python
└── README.md
```

## Seguridad

- Tu API key nunca se envia a ningun servidor excepto la API de Anthropic
- Los PDFs se procesan localmente en tu maquina
- El archivo `.env` esta excluido del control de versiones via `.gitignore`
- Si usas 1Password o macOS Keychain, la key queda protegida por el sistema operativo

## Licencia

MIT
