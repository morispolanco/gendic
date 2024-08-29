import streamlit as st
import requests
import json
from docx import Document
from io import BytesIO

# Set page configuration
st.set_page_config(page_title="Generador de Estructura de Libro", page_icon="📚", layout="wide")

# Function to create the information column
def crear_columna_info():
    st.markdown("""
    ## Sobre esta aplicación

    Esta aplicación genera una estructura de libro con capítulos, descripciones breves y citas relevantes en formato APA.

    ### Cómo usar la aplicación:

    1. Ingrese el título del libro.
    2. Especifique el número de capítulos (máximo 15).
    3. Defina la audiencia objetivo.
    4. Añada observaciones adicionales si lo desea.
    5. Genere la estructura del libro.
    6. Descargue el documento DOCX con la estructura y las citas.

    ### Autor:
    **Moris Polanco**, [Fecha actual]

    ---
    **Nota:** Verifique la información con fuentes adicionales para un análisis más profundo.
    """)

# Titles and Main Column
st.title("Generador de Estructura de Libro")

col1, col2 = st.columns([1, 2])

with col1:
    crear_columna_info()

with col2:
    TOGETHER_API_KEY = st.secrets["TOGETHER_API_KEY"]
    SERPLY_API_KEY = st.secrets["SERPLY_API_KEY"]

    def generar_capitulos(titulo_libro, num_capitulos, audiencia, observaciones):
        url = "https://api.together.xyz/inference"
        payload = json.dumps({
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "prompt": f"Genera una lista de {num_capitulos} capítulos para un libro titulado '{titulo_libro}'. La audiencia objetivo es: {audiencia}. Observaciones adicionales: {observaciones}. Cada capítulo debe estar en una línea nueva.",
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
        capitulos = response.json()['output']['choices'][0]['text'].strip().split('\n')
        return [capitulo.strip() for capitulo in capitulos if capitulo.strip()]

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

    def generar_descripcion(capitulo, contexto):
        url = "https://api.together.xyz/inference"
        payload = json.dumps({
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "prompt": f"Proporciona una descripción breve y concisa del capítulo '{capitulo}' basada en el siguiente contexto. La descripción debe tener aproximadamente 50 palabras:\n\nContexto: {contexto}\n\nDescripción:",
            "max_tokens": 1024,
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
        return response.json()['output']['choices'][0]['text'].strip()

    def create_docx(titulo_libro, capitulos_descripciones, citas):
        doc = Document()
        doc.add_heading(f'Estructura del libro: {titulo_libro}', 0)

        # Capítulos y descripciones
        doc.add_heading('Capítulos y Descripciones', level=1)
        for capitulo, descripcion in capitulos_descripciones.items():
            doc.add_heading(capitulo, level=2)
            doc.add_paragraph(descripcion)

        # Citas
        doc.add_page_break()
        doc.add_heading('Citas Relevantes', level=1)
        for cita in citas:
            doc.add_paragraph(cita, style='List Bullet')

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
    titulo_libro = st.text_input("Ingresa el título del libro:")
    num_capitulos = st.number_input("Número de capítulos:", min_value=1, max_value=15, value=5)
    audiencia = st.text_input("Audiencia objetivo:")
    observaciones = st.text_area("Observaciones adicionales:")

    if st.button("Generar estructura del libro"):
        if titulo_libro and audiencia:
            with st.spinner("Generando estructura del libro..."):
                capitulos = generar_capitulos(titulo_libro, num_capitulos, audiencia, observaciones)
                st.session_state.capitulos = capitulos

    if 'capitulos' in st.session_state:
        st.subheader("Capítulos generados:")
        for capitulo in st.session_state.capitulos:
            st.write(capitulo)

        if st.button("Generar descripciones y citas"):
            with st.spinner("Generando descripciones y citas..."):
                capitulos_descripciones = {}
                todas_citas = []

                for capitulo in st.session_state.capitulos:
                    resultados_busqueda = buscar_informacion(f"{capitulo} {titulo_libro}")
                    contexto = "\n".join([item["snippet"] for item in resultados_busqueda.get("results", [])])
                    descripcion = generar_descripcion(capitulo, contexto)
                    capitulos_descripciones[capitulo] = descripcion
                    citas = [formatear_referencia_apa(item) for item in resultados_busqueda.get("results", [])[:2]]  # Tomamos solo 2 citas por capítulo
                    todas_citas.extend(citas)

                st.subheader("Descripciones de capítulos:")
                for capitulo, descripcion in capitulos_descripciones.items():
                    st.markdown(f"**{capitulo}**: {descripcion}")

                st.subheader("Citas relevantes:")
                for cita in todas_citas[:10]:  # Limitamos a 10 citas en total
                    st.markdown(f"- {cita}")

                # Botón para descargar el documento
                doc = create_docx(titulo_libro, capitulos_descripciones, todas_citas[:10])
                buffer = BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                st.download_button(
                    label="Descargar estructura del libro en DOCX",
                    data=buffer,
                    file_name=f"Estructura_{titulo_libro.replace(' ', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
