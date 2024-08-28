import streamlit as st
import requests
import json
from docx import Document
from io import BytesIO

# Set page configuration
st.set_page_config(page_title="Generador de Diccionario por Campo de Estudio", page_icon="📚", layout="wide")

# Function to create the information column
def crear_columna_info():
    st.markdown("""
    ## Sobre esta aplicación

    Esta aplicación es un Generador de Diccionario que permite a los usuarios crear un diccionario personalizado basado en un campo o área de estudio específico.

    ### Cómo usar la aplicación:

    1. Ingrese un campo o área de estudio de su interés.
    2. Haga clic en "Generar términos" para obtener una lista de 101 términos relacionados.
    3. Edite la lista de términos según sea necesario.
    4. Seleccione si desea generar definiciones para todos los términos o para un término específico.
    5. Haga clic en "Generar definiciones" para obtener las definiciones.
    6. Lea las definiciones y las fuentes proporcionadas.
    7. Si lo desea, descargue un documento DOCX con toda la información.

    ### Autor y actualización:
    **Moris Polanco**, [Fecha actual]

    ### Cómo citar esta aplicación (formato APA):
    Polanco, M. (2024). *Generador de Diccionario por Campo de Estudio* [Aplicación web]. [URL de la aplicación]

    ---
    **Nota:** Esta aplicación utiliza inteligencia artificial para generar términos y definiciones. Verifique la información con fuentes adicionales para un análisis más profundo.
    """)

# Titles and Main Column
st.title("Generador de Diccionario por Campo de Estudio")

col1, col2 = st.columns([1, 2])

with col1:
    crear_columna_info()

with col2:
    TOGETHER_API_KEY = st.secrets["TOGETHER_API_KEY"]
    SERPLY_API_KEY = st.secrets["SERPLY_API_KEY"]

    def generar_terminos(campo_estudio):
        url = "https://api.together.xyz/inference"
        payload = json.dumps({
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "prompt": f"Genera una lista de 101 términos relacionados con el campo de estudio: {campo_estudio}. Cada término debe estar en una línea nueva.",
            "max_tokens": 2048,
            "temperature": 0.7,
            "top_p": 0.7,
            "top_k": 50,
            "repetition_penalty": 1,
        })
        headers = {
            'Authorization': f'Bearer {TOGETHER_API_KEY}',
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, data=payload)
        terminos = response.json()['output']['choices'][0]['text'].strip().split('\n')
        return [termino.strip() for termino in terminos if termino.strip()]

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
            "prompt": f"Contexto: {contexto}\n\nTérmino: {termino}\n\nProporciona una definición detallada del término '{termino}'. La definición debe ser informativa, similar a una entrada de diccionario extendida. Incluye conceptos relacionados si es relevante.\n\nDefinición:",
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

    def create_docx(campo_estudio, terminos_definiciones):
        doc = Document()
        doc.add_heading(f'Diccionario de {campo_estudio}', 0)

        for termino, definicion in terminos_definiciones.items():
            doc.add_heading(termino, level=1)
            doc.add_paragraph(definicion)

        doc.add_paragraph('\nNota: Este documento fue generado por un asistente de IA. Verifica la información con fuentes académicas para un análisis más profundo.')

        return doc

    # Interfaz de usuario
    campo_estudio = st.text_input("Ingresa un campo o área de estudio:")

    if st.button("Generar términos"):
        if campo_estudio:
            with st.spinner("Generando términos..."):
                terminos = generar_terminos(campo_estudio)
                st.session_state.terminos = terminos

    if 'terminos' in st.session_state:
        st.subheader("Lista de términos (editable):")
        terminos_editados = st.text_area("Edita los términos aquí:", "\n".join(st.session_state.terminos), height=300)
        st.session_state.terminos_editados = terminos_editados.split('\n')

    if 'terminos_editados' in st.session_state:
        opcion_definicion = st.radio("Selecciona una opción:", ["Generar todas las definiciones", "Generar definición para un término específico"])

        if opcion_definicion == "Generar definición para un término específico":
            termino_seleccionado = st.selectbox("Selecciona un término:", st.session_state.terminos_editados)

        if st.button("Generar definiciones"):
            with st.spinner("Generando definiciones..."):
                terminos_definiciones = {}
                if opcion_definicion == "Generar todas las definiciones":
                    for termino in st.session_state.terminos_editados:
                        resultados_busqueda = buscar_informacion(f"{termino} {campo_estudio}")
                        contexto = "\n".join([item["snippet"] for item in resultados_busqueda.get("results", [])])
                        definicion = generar_definicion(termino, contexto)
                        terminos_definiciones[termino] = definicion
                else:
                    resultados_busqueda = buscar_informacion(f"{termino_seleccionado} {campo_estudio}")
                    contexto = "\n".join([item["snippet"] for item in resultados_busqueda.get("results", [])])
                    definicion = generar_definicion(termino_seleccionado, contexto)
                    terminos_definiciones[termino_seleccionado] = definicion

                st.subheader("Definiciones generadas:")
                for termino, definicion in terminos_definiciones.items():
                    st.markdown(f"**{termino}**: {definicion}")

                # Botón para descargar el documento
                doc = create_docx(campo_estudio, terminos_definiciones)
                buffer = BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                st.download_button(
                    label="Descargar diccionario en DOCX",
                    data=buffer,
                    file_name=f"Diccionario_{campo_estudio.replace(' ', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
