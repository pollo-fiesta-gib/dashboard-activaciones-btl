import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import re

# Configuración de la página
st.set_page_config(page_title="BTL Command Center", layout="wide")

st.title("🎯 Centro de Control - Activaciones Pollo Fiesta")
st.markdown("---")

# URL de tu Google Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/1fFcgK4ikmaEDXXesAc7wljONAyYx0b-0DAhjGa4vZqg/export?format=csv"

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

if df is not None and len(df) > 0:
    st.success(f"✅ Datos cargados correctamente - {len(df)} activaciones registradas")
    
    # ========== DIAGNÓSTICO: MOSTRAR TODAS LAS COLUMNAS ==========
    st.markdown("## 🔍 DIAGNÓSTICO - Columnas disponibles")
    st.write("**Columnas en tu archivo:**")
    
    # Mostrar todas las columnas en una tabla
    columnas_df = pd.DataFrame({
        'Número': range(1, len(df.columns) + 1),
        'Nombre de columna': df.columns.tolist()
    })
    st.dataframe(columnas_df, use_container_width=True)
    
    # Mostrar una muestra de los datos
    st.markdown("## 📊 Muestra de datos (primeras 3 filas)")
    st.dataframe(df.head(3), use_container_width=True)
    
    # ========== ANÁLISIS DE COLUMNAS CRÍTICAS ==========
    st.markdown("## 🔍 Verificación de columnas críticas")
    
    columnas_criticas = {
        'Fecha': ['Fecha de Activación', 'Fecha', 'FECHA'],
        'Activador': ['Activador de Marca', 'Activador', 'ACTIVADOR'],
        'Canal': ['Canal de Activación', 'Canal', 'CANAL'],
        'Meta': ['¿Se cumplió la meta?', 'Cumplió meta', 'META'],
        'Ventas': ['Ventas netas aproximadas', 'Ventas', 'VENTAS'],
        'Ticket': ['Ticket promedio estimado', 'Ticket', 'TICKET'],
        'Ubicación': ['Lugar / Dirección del punto', 'Ubicación', 'UBICACIÓN']
    }
    
    resultados = []
    for categoria, posibles in columnas_criticas.items():
        encontrada = None
        for col in df.columns:
            if col in posibles or col.strip() in posibles:
                encontrada = col
                break
        if encontrada:
            # Mostrar algunos valores de ejemplo
            valores = df[encontrada].dropna().head(3).tolist()
            resultados.append({
                'Categoría': categoria,
                'Columna encontrada': encontrada,
                'Valores de ejemplo': str(valores)
            })
        else:
            resultados.append({
                'Categoría': categoria,
                'Columna encontrada': '❌ NO ENCONTRADA',
                'Valores de ejemplo': '-'
            })
    
    st.dataframe(pd.DataFrame(resultados), use_container_width=True)
    
    # ========== MOSTRAR DATOS EN TABLA SIMPLE ==========
    st.markdown("## 📋 Datos completos")
    st.dataframe(df, use_container_width=True, height=400)
    
else:
    st.error("❌ No se pudieron cargar los datos. Verifica la URL de Google Sheets.")
