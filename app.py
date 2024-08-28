import streamlit as st
import requests
import json
from docx import Document
from io import BytesIO

# Set page configuration
st.set_page_config(page_title="Generador de Diccionario Especializado", page_icon="📚", layout="wide")

# Function to create the information column
def crear_columna_info():
    st.markdown("""
    ## Sobre esta aplicación

    Esta aplicación genera un diccionario especializado con definiciones concisas y referencias académicas en formato APA.

    ### Cómo usar la aplicación:

    1. Ingrese un campo o área de estudio.
    2. Genere y edite la lista de términos.
    3. Genere definiciones para todos los términos o para uno específico.
    4. Descargue el documento DOCX con definiciones y referencias.

    ### Autor:
    **Moris Polanco**, [Fecha actual]

    ---
    **Nota:** Verifique la información con fuentes adicionales para un análisis más profundo.
    """)

# Titles and Main Column
st.title("Generador de Diccionario Especializado")

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
            "prompt": f"Proporciona una definición concisa y precisa del término '{termino}' basada en el siguiente contexto académico. No incluyas ejemplos, sinónimos, antónimos ni conceptos relacionados. Solo la definición:\n\nContexto: {contexto}\n\nDefinición:",
            "max_tokens": 1024,
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

    def create_docx(campo_estudio, terminos_definiciones, referencias):
        doc = Document()
        doc.add_heading(f'Diccionario de {campo_estudio}', 0)

        # Definiciones
        doc.add_heading('Definiciones', level=1)
        for termino, definicion in terminos_definiciones.items():
            doc.add_paragraph(f"{termino}: {definicion}")

        # Referencias
        doc.add_page_break()
        doc.add_heading('Referencias', level=1)
        for referencia in referencias:
            doc.add_paragraph(referencia, style='List Bullet')

        return doc

    def formatear_referencia_apa(ref):
        authors = ref.get('author', 'Autor desconocido')
        year = ref.get('year', 's.f.')
        title = ref.get('title', 'Título desconocido')
        journal = ref.get('journal', '')
        volume = ref.get('volume', '')
        issue = ref.get('issue', '')
        pages = ref.get('pages', '')
        url = ref.get('url', '')

        reference = f"{authors} ({year}). {title}."
        if journal:
            reference += f" {journal}"
            if volume:
                reference += f", {volume}"
                if issue:
                    reference += f"({issue})"
            if pages:
                reference += f", {pages}"
        reference += f". {url}"
        
        return reference

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
            with st.spinner("Generando definiciones y referencias..."):
                terminos_definiciones = {}
                todas_referencias = []

                if opcion_definicion == "Generar todas las definiciones":
                    for termino in st.session_state.terminos_editados:
                        resultados_busqueda = buscar_informacion(f"{termino} {campo_estudio}")
                        contexto = "\n".join([item["snippet"] for item in resultados_busqueda.get("results", [])])
                        definicion = generar_definicion(termino, contexto)
                        terminos_definiciones[termino] = definicion
                        referencias = [formatear_referencia_apa(item) for item in resultados_busqueda.get("results", [])]
                        todas_referencias.extend(referencias)
                else:
                    resultados_busqueda = buscar_informacion(f"{termino_seleccionado} {campo_estudio}")
                    contexto = "\n".join([item["snippet"] for item in resultados_busqueda.get("results", [])])
                    definicion = generar_definicion(termino_seleccionado, contexto)
                    terminos_definiciones[termino_seleccionado] = definicion
                    referencias = [formatear_referencia_apa(item) for item in resultados_busqueda.get("results", [])]
                    todas_referencias.extend(referencias)

                st.subheader("Definiciones generadas:")
                for termino, definicion in terminos_definiciones.items():
                    st.markdown(f"**{termino}**: {definicion}")

                st.subheader("Referencias:")
                for referencia in todas_referencias:
                    st.markdown(f"- {referencia}")

                # Botón para descargar el documento
                doc = create_docx(campo_estudio, terminos_definiciones, todas_referencias)
                buffer = BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                st.download_button(
                    label="Descargar diccionario en DOCX",
                    data=buffer,
                    file_name=f"Diccionario_{campo_estudio.replace(' ', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
