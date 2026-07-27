import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="BTL Command Center", layout="wide")

# Título principal
st.title("🎯 Centro de Control - Activaciones Pollo Fiesta")
st.markdown("---")

# 🔴 URL de tu Google Sheets
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
    
    # 1️⃣ KPIs PRINCIPALES
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total Activaciones", len(df))
    
    with col2:
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
    
    # 2️⃣ GRÁFICOS PRINCIPALES (VERSIÓN CORREGIDA)
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Activaciones por Activador")
        if 'Activador de Marca' in df.columns:
            # CORREGIDO: Crear el DataFrame de forma más clara
            conteo_activadores = df['Activador de Marca'].value_counts().reset_index()
            conteo_activadores.columns = ['Activador', 'Número de Activaciones']  # Renombrar columnas
            
            fig1 = px.bar(
                conteo_activadores,
                x='Activador',
                y='Número de Activaciones',
                title="Número de activaciones por activador",
                color='Activador',
                text='Número de Activaciones'
            )
            fig1.update_traces(textposition='outside')
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Columna 'Activador de Marca' no encontrada")
    
    with col2:
        st.subheader("🏪 Activaciones por Canal")
        if 'Canal de Activación' in df.columns:
            # CORREGIDO: Gráfico de pastel más simple
            conteo_canal = df['Canal de Activación'].value_counts().reset_index()
            conteo_canal.columns = ['Canal', 'Número de Activaciones']
            
            fig2 = px.pie(
                conteo_canal,
                names='Canal',
                values='Número de Activaciones',
                title="Distribución por canal"
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Columna 'Canal de Activación' no encontrada")
    
    st.markdown("---")
    
    # 3️⃣ ANÁLISIS DE CUMPLIMIENTO
    st.subheader("📈 Análisis de Cumplimiento de Meta")
    col1, col2 = st.columns(2)
    
    with col1:
        if '¿Se cumplió la meta?' in df.columns:
            fig3 = px.pie(
                df,
                names='¿Se cumplió la meta?',
                title="Cumplimiento de Meta",
                color_discrete_map={'Si': '#2ecc71', 'No': '#e74c3c', 'Parcialmente': '#f39c12'}
            )
            st.plotly_chart(fig3, use_container_width=True)
    
    with col2:
        if 'Canal de Activación' in df.columns and '¿Se cumplió la meta?' in df.columns:
            # Tabla de cumplimiento por canal
            cumplimiento_canal = df.groupby('Canal de Activación')['¿Se cumplió la meta?'].apply(
                lambda x: (x == 'Si').sum() / len(x) * 100
            ).reset_index()
            cumplimiento_canal.columns = ['Canal', '% Cumplimiento']
            
            fig4 = px.bar(
                cumplimiento_canal,
                x='Canal',
                y='% Cumplimiento',
                title="% Cumplimiento por Canal",
                color='Canal',
                text='% Cumplimiento'
            )
            fig4.update_traces(textposition='outside')
            fig4.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig4, use_container_width=True)
    
    st.markdown("---")
    
    # 4️⃣ ANÁLISIS DE INCIDENCIAS (Blindaje)
    st.subheader("🛡️ Análisis de Incidencias (Blindaje)")
    
    columnas_texto = ['Observaciones del estado inicial', '¿Alguna novedad relevante durante la activación?', 'Oportunidades de mejora para próxima activación']
    incidencias = {}
    
    for col in columnas_texto:
        if col in df.columns:
            for palabra in ['lluvia', 'clima', 'competencia', 'poca afluencia', 'inventario']:
                count = df[col].str.lower().str.contains(palabra, na=False).sum()
                if count > 0:
                    if palabra not in incidencias:
                        incidencias[palabra] = 0
                    incidencias[palabra] += count
    
    if incidencias:
        # Crear DataFrame para mostrar
        df_incidencias = pd.DataFrame(list(incidencias.items()), columns=['Incidencia', 'Casos'])
        fig5 = px.bar(
            df_incidencias,
            x='Incidencia',
            y='Casos',
            title="Incidencias reportadas en campo",
            color='Incidencia',
            text='Casos'
        )
        fig5.update_traces(textposition='outside')
        st.plotly_chart(fig5, use_container_width=True)
        
        # Mostrar tabla de activaciones con incidencias
        st.subheader("📋 Activaciones con incidencias detectadas")
        filas_con_incidencia = []
        for col in columnas_texto:
            if col in df.columns:
                for palabra in ['lluvia', 'clima', 'competencia', 'poca afluencia', 'inventario']:
                    mascara = df[col].str.lower().str.contains(palabra, na=False)
                    if mascara.sum() > 0:
                        filas = df[mascara][['Fecha de Activación', 'Activador de Marca', 'Canal de Activación', '¿Se cumplió la meta?', col]].copy()
                        filas['Incidencia detectada'] = palabra
                        filas_con_incidencia.append(filas)
        
        if filas_con_incidencia:
            df_incidencias_tabla = pd.concat(filas_con_incidencia)
            st.dataframe(df_incidencias_tabla.head(20), use_container_width=True)
    else:
        st.info("✅ No se detectaron incidencias importantes en las activaciones")
    
    st.markdown("---")
    st.caption(f"🔄 Actualizado automáticamente desde Google Forms - Última carga: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

else:
    st.error("❌ No se pudieron cargar los datos. Verifica la URL de Google Sheets.")
    st.info("Asegúrate de que el archivo esté compartido como 'Cualquier persona con el enlace puede ver'")
