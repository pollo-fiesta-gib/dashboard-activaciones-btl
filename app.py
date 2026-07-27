import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="BTL Command Center", layout="wide")

# Título principal
st.title("🎯 Centro de Control - Activaciones Pollo Fiesta")
st.markdown("---")

# 🔴 URL de tu Google Sheets (YA ACTUALIZADA CON TU URL)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1fFcgK4ikmaEDXXesAc7wljONAyYx0b-0DAhjGa4vZqg/export?format=csv"

# Función para cargar datos con caché
@st.cache_data(ttl=3600)
def cargar_datos():
    try:
        df = pd.read_csv(SHEET_URL)
        return df
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return None

# Cargar datos
df = cargar_datos()

if df is not None:
    # Mostrar datos cargados
    st.success(f"✅ Datos cargados correctamente - {len(df)} activaciones registradas")
    
    # Mostrar una vista previa
    with st.expander("👁️ Ver datos crudos (primeras 5 filas)"):
        st.dataframe(df.head())
    
    st.markdown("---")
    
    # 1️⃣ KPIs PRINCIPALES (Métricas de alto nivel)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total Activaciones", len(df))
    
    with col2:
        # Calcular cumplimiento de meta
        if '¿Se cumplió la meta?' in df.columns:
            cumplimiento = df['¿Se cumplió la meta?'].value_counts(normalize=True).get('Si', 0) * 100
            st.metric("🎯 Cumplimiento Meta", f"{cumplimiento:.0f}%")
        else:
            st.metric("🎯 Cumplimiento Meta", "N/A")
    
    with col3:
        if 'Activador de Marca' in df.columns:
            activadores = df['Activador de Marca'].nunique()
            st.metric("👤 Activadores", activadores)
        else:
            st.metric("👤 Activadores", "N/A")
    
    with col4:
        if 'Canal de Activación' in df.columns:
            canales = df['Canal de Activación'].nunique()
            st.metric("🏪 Canales", canales)
        else:
            st.metric("🏪 Canales", "N/A")
    
    st.markdown("---")
    
    # 2️⃣ GRÁFICOS PRINCIPALES
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Activaciones por Activador")
        if 'Activador de Marca' in df.columns:
            fig1 = px.bar(
                df['Activador de Marca'].value_counts().reset_index(),
                x='index', 
                y='count',
                title="Número de activaciones por activador",
                color='index',
                labels={'index': 'Activador', 'count': 'Número de activaciones'}
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Columna 'Activador de Marca' no encontrada")
    
    with col2:
        st.subheader("🏪 Activaciones por Canal")
        if 'Canal de Activación' in df.columns:
            fig2 = px.pie(
                df, 
                names='Canal de Activación',
                title="Distribución por canal"
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Columna 'Canal de Activación' no encontrada")
    
    # 3️⃣ TABLA DE ÚLTIMAS ACTIVACIONES
    st.subheader("📋 Últimas activaciones reportadas")
    if 'Fecha de Activación' in df.columns:
        df_ultimas = df[['Fecha de Activación', 'Activador de Marca', 'Canal de Activación', '¿Se cumplió la meta?']].head(10)
        st.dataframe(df_ultimas, use_container_width=True)
    else:
        st.info("No se puede mostrar la tabla de últimas activaciones")
    
    # 4️⃣ ANÁLISIS DE INCIDENCIAS (Blindaje)
    st.markdown("---")
    st.subheader("🛡️ Análisis de Incidencias (Blindaje)")
    
    # Buscar palabras clave en las columnas de texto
    columnas_texto = ['Observaciones del estado inicial', '¿Alguna novedad relevante durante la activación?', 'Oportunidades de mejora para próxima activación']
    incidencias = []
    
    for col in columnas_texto:
        if col in df.columns:
            # Buscar palabras clave
            for palabra in ['lluvia', 'clima', 'competencia', 'poca afluencia', 'inventario']:
                count = df[col].str.lower().str.contains(palabra, na=False).sum()
                if count > 0:
                    incidencias.append(f"'{palabra}': {count} casos")
    
    if incidencias:
        st.write("**Incidencias detectadas en las activaciones:**")
        for inc in incidencias:
            st.write(f"- {inc}")
    else:
        st.info("No se detectaron incidencias importantes")
    
    st.markdown("---")
    st.caption(f"🔄 Actualizado automáticamente desde Google Forms - Última carga: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

else:
    st.error("❌ No se pudieron cargar los datos. Verifica la URL de Google Sheets.")
    st.info("Asegúrate de que el archivo esté compartido como 'Cualquier persona con el enlace puede ver'")