import streamlit as st
import requests
import json
from docx import Document
from io import BytesIO

# Set page configuration
st.set_page_config(page_title="Diccionario Económico Austríaco", page_icon="📚", layout="wide")

# Function to create the information column
def crear_columna_info():
    st.markdown("""
    ## Sobre esta aplicación

    Esta aplicación es un Diccionario Económico basado en la perspectiva de la Escuela Austríaca de Economía. Permite a los usuarios obtener definiciones de términos económicos según esta interpretación.

    ### Cómo usar la aplicación:

    1. Elija un campo o área de estudio.
    2. Genere 101 términos relacionados con esa área.
    3. Edite la lista de términos si es necesario.
    4. Haga clic en "Generar todas las definiciones" para obtener las definiciones desde la perspectiva de la escuela austríaca.
    5. Lea las definiciones y las fuentes proporcionadas.
    6. Si lo desea, descargue un documento DOCX con toda la información.

    ### Autor y actualización:
    **Moris Polanco**, 28 ag 2024

    ### Cómo citar esta aplicación (formato APA):
    Polanco, M. (2024). *Diccionario Económico Austríaco* [Aplicación web]. https://escuelaaustriaca.streamlit.app

    ---
    **Nota:** Esta aplicación utiliza inteligencia artificial para generar definiciones basadas en la visión de la escuela austríaca. Verifique la información con fuentes adicionales para un análisis más profundo.
    """)

# Titles and Main Column
st.title("Diccionario Económico Austríaco")

col1, col2 = st.columns([1, 2])

with col1:
    crear_columna_info()

with col2:
    TOGETHER_API_KEY = st.secrets["TOGETHER_API_KEY"]
    SERPLY_API_KEY = st.secrets["SERPLY_API_KEY"]

    def buscar_informacion(query):
        url = f"https://api.serply.io/v1/scholar/q={query}"
        headers = {
            'X-Api-Key': SERPLY_API_KEY,
            'Content-Type': 'application/json',
            'X-Proxy-Location': 'US',
            'X-User-Agent': 'Mozilla/5.0'
        }
        response = requests.get(url, headers=headers)
        return response.json()

    def generar_definicion(termino, contexto):
        url = "https://api.together.xyz/inference"
        payload = json.dumps({
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "prompt": f"Contexto: {contexto}\n\nTérmino: {termino}\n\nProporciona una definición del término económico '{termino}' según la visión de la escuela austríaca de economía. La definición debe ser más larga, detallada, e informativa, similar a una entrada de diccionario extendida. Incluye referencias a fuentes específicas que traten este concepto.\n\nDefinición:",
            "max_tokens": 2048,
            "temperature": 0.7,
            "top_p": 0.7,
            "top_k": 50,
            "repetition_penalty": 1,
            "stop": ["Término:"]
        })
        headers = {
            'Authorization': f'Bearer {TOGETHER_API_KEY}',
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, data=payload)
        return response.json()['output']['choices'][0]['text'].strip()

    def create_docx(definiciones):
        doc = Document()
        doc.add_heading('Diccionario Económico - Escuela Austríaca', 0)

        for termino, (definicion, fuentes) in definiciones.items():
            doc.add_heading(termino, level=1)
            doc.add_paragraph(definicion)

            if fuentes:
                doc.add_heading('Fuentes', level=2)
                for fuente in fuentes:
                    doc.add_paragraph(f"{fuente['author']}. ({fuente['year']}). *{fuente['title']}*. {fuente['journal']}, {fuente['volume']}({fuente['issue']}), {fuente['pages']}. {fuente['url']}", style='List Bullet')

            doc.add_paragraph('\nNota: Este documento fue generado por un asistente de IA. Verifica la información con fuentes académicas para un análisis más profundo.')

        return doc

    st.write("Propón un campo o área de estudio:")

    campo_estudio = st.text_input("Ingresa un campo o área de estudio:")

    if st.button("Generar términos"):
        if campo_estudio:
            # Replace this with actual logic to generate terms related to the field of study
            terminos_generados = [f"Término {i+1}" for i in range(101)]
            terminos_editados = st.text_area("Edita la lista de términos:", "\n".join(terminos_generados),
                                             height=400)
            terminos = terminos_editados.split("\n")
            st.session_state.terminos_generados = terminos
        else:
            st.warning("Por favor, ingresa un campo o área de estudio.")

    if 'terminos_generados' in st.session_state:
        if st.button("Generar todas las definiciones"):
            if st.session_state.terminos_generados:
                contex_dict = {}
                with st.spinner("Buscando información y generando definiciones..."):
                    definiciones = {}
                    for termino in st.session_state.terminos_generados:
                        resultados_busqueda = buscar_informacion(termino)
                        contexto = "\n".join([item["snippet"] for item in resultados_busqueda.get("results", [])])
                        fuentes = [{
                            "author": item.get("author", "Autor desconocido"),
                            "year": item.get("year", "s.f."),
                            "title": item.get("title"),
                            "journal": item.get("journal", "Revista desconocida"),
                            "volume": item.get("volume", ""),
                            "issue": item.get("issue", ""),
                            "pages": item.get("pages", ""),
                            "url": item.get("url")
                        } for item in resultados_busqueda.get("results", [])]
                        definicion = generar_definicion(termino, contexto)
                        definiciones[termino] = (definicion, fuentes)

                # Mostrar definiciones
                for termino, (definicion, _) in definiciones.items():
                    st.subheader(f"Definición para el término: {termino}")
                    st.markdown(f"**{definicion}**")

                # Botón para descargar el documento
                doc = create_docx(definiciones)
                buffer = BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                st.download_button(
                    label="Descargar definiciones en DOCX",
                    data=buffer,
                    file_name="Definiciones_Diccionario_Económico.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            else:
                st.warning("La lista de términos está vacía.")
