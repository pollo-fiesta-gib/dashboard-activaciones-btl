import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import re

# Configuración de la página
st.set_page_config(
    page_title="BTL Command Center", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.markdown("""
<div style="text-align: center; padding: 0.5rem 0;">
    <h1 style="font-size: 2.2rem;">🎯 Activaciones BTL - Pollo Fiesta</h1>
    <p style="color: #666; font-size: 1rem;">Panel de control ejecutivo</p>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# URL de tu Google Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/1fFcgK4ikmaEDXXesAc7wljONAyYx0b-0DAhjGa4vZqg/export?format=csv"

# Funciones de limpieza
def limpiar_ventas(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor) if valor > 0 else None
    if isinstance(valor, str):
        numeros = re.findall(r'[\d,]+', valor)
        if numeros:
            try:
                return float(numeros[0].replace(',', ''))
            except:
                return None
    return None

def limpiar_ticket(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor) if valor > 0 else None
    if isinstance(valor, str):
        limpio = re.sub(r'[^\d,]', '', valor)
        if limpio:
            try:
                return float(limpio.replace(',', ''))
            except:
                return None
    return None

def convertir_fecha_segura(fecha_str):
    if pd.isna(fecha_str):
        return pd.NaT
    try:
        return pd.to_datetime(fecha_str, errors='coerce')
    except:
        return pd.NaT

@st.cache_data(ttl=3600)
def cargar_datos():
    try:
        df = pd.read_csv(SHEET_URL)
        
        # Ventas
        col_ventas = 'Ventas netas aproximadas (en kilos, poner únicamente cifra)'
        if col_ventas in df.columns:
            df['Ventas_netas_limpias'] = df[col_ventas].apply(limpiar_ventas)
        
        # Ticket
        col_ticket = 'Ticket promedio estimado?'
        if col_ticket in df.columns:
            df['Ticket_limpo'] = df[col_ticket].apply(limpiar_ticket)
        
        # Detectar incidencias
        columnas_incidencias = []
        for col in df.columns:
            if 'Observaciones' in col or 'novedad' in col.lower() or 'Oportunidades' in col or 'mejora' in col.lower():
                columnas_incidencias.append(col)
        
        df['Texto_completo'] = ''
        for col in columnas_incidencias:
            df['Texto_completo'] = df['Texto_completo'].fillna('') + ' ' + df[col].fillna('')
        
        incidencias_keywords = {
            '🌧️ Lluvia': ['lluvia', 'lluvioso', 'lloviendo'],
            '🌡️ Clima': ['clima', 'frío', 'calor'],
            '🏪 Competencia': ['competencia', 'competidor'],
            '👥 Poca afluencia': ['poca afluencia', 'poco público', 'baja afluencia'],
            '📦 Logística': ['inventario', 'pedido', 'retraso', 'demora'],
        }
        
        df['Incidencias_detectadas'] = 'Sin incidencias'
        for idx, row in df.iterrows():
            texto = str(row['Texto_completo']).lower()
            incidencias = []
            for categoria, palabras in incidencias_keywords.items():
                for palabra in palabras:
                    if palabra in texto:
                        incidencias.append(categoria)
                        break
            if incidencias:
                df.at[idx, 'Incidencias_detectadas'] = ', '.join(incidencias)
        
        # Convertir fechas
        col_fecha = 'Fecha de Activación'
        if col_fecha in df.columns:
            df['Fecha'] = df[col_fecha].apply(convertir_fecha_segura)
            df = df.dropna(subset=['Fecha'])
            df['Mes'] = df['Fecha'].dt.strftime('%B %Y')
        
        return df
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return None

# Cargar datos
df = cargar_datos()

if df is not None and len(df) > 0:
    
    # ==================== FILTROS ====================
    with st.sidebar:
        st.markdown("## 🔍 Filtros")
        
        if 'Activador de Marca' in df.columns:
            activadores = ['Todos'] + list(df['Activador de Marca'].unique())
            activador_seleccionado = st.selectbox("👤 Activador", activadores)
        else:
            activador_seleccionado = 'Todos'
        
        if 'Canal de Activación' in df.columns:
            canales = ['Todos'] + list(df['Canal de Activación'].unique())
            canal_seleccionado = st.selectbox("🏪 Canal", canales)
        else:
            canal_seleccionado = 'Todos'
        
        if 'Mes' in df.columns:
            meses_disponibles = sorted(df['Mes'].unique(), key=lambda x: datetime.strptime(x, '%B %Y'))
            meses = ['Todos los meses'] + meses_disponibles
            mes_seleccionado = st.selectbox("📅 Mes", meses)
        else:
            mes_seleccionado = 'Todos los meses'
        
        st.markdown("---")
        st.info(f"📊 {len(df)} activaciones totales")
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    if activador_seleccionado != 'Todos' and 'Activador de Marca' in df.columns:
        df_filtrado = df_filtrado[df_filtrado['Activador de Marca'] == activador_seleccionado]
    
    if canal_seleccionado != 'Todos' and 'Canal de Activación' in df.columns:
        df_filtrado = df_filtrado[df_filtrado['Canal de Activación'] == canal_seleccionado]
    
    if mes_seleccionado != 'Todos los meses' and 'Mes' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['Mes'] == mes_seleccionado]
    
    # ==================== KPIs PRINCIPALES ====================
    st.markdown("## 📊 Resumen Ejecutivo")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Activaciones", len(df_filtrado))
    
    with col2:
        if '¿Se cumplió la meta?' in df_filtrado.columns:
            cumplimiento = df_filtrado['¿Se cumplió la meta?'].value_counts(normalize=True).get('Si', 0) * 100
            color = "🟢" if cumplimiento >= 80 else "🟡" if cumplimiento >= 50 else "🔴"
            st.metric(f"{color} Cumplimiento", f"{cumplimiento:.0f}%")
        else:
            st.metric("🎯 Cumplimiento", "N/A")
    
    with col3:
        if 'Ventas_netas_limpias' in df_filtrado.columns:
            total_ventas = df_filtrado['Ventas_netas_limpias'].sum()
            if pd.notna(total_ventas) and total_ventas > 0:
                st.metric("💰 Ventas (kg)", f"{total_ventas:,.0f}")
            else:
                st.metric("💰 Ventas (kg)", "Sin datos")
    
    with col4:
        if 'Ticket_limpo' in df_filtrado.columns:
            ticket_promedio = df_filtrado['Ticket_limpo'].dropna()
            ticket_promedio = ticket_promedio[ticket_promedio > 0]
            if len(ticket_promedio) > 0:
                st.metric("💳 Ticket promedio", f"${ticket_promedio.mean():,.0f}")
            else:
                st.metric("💳 Ticket promedio", "Sin datos")
    
    st.markdown("---")
    
    # ==================== SEMÁFORO DE CUMPLIMIENTO POR CANAL ====================
    st.markdown("## 🚦 Semáforo de Cumplimiento por Canal")
    
    if 'Canal de Activación' in df_filtrado.columns and '¿Se cumplió la meta?' in df_filtrado.columns:
        # Calcular cumplimiento por canal
        cumplimiento_canal = df_filtrado.groupby('Canal de Activación')['¿Se cumplió la meta?'].apply(
            lambda x: (x == 'Si').sum() / len(x) * 100
        ).reset_index()
        cumplimiento_canal.columns = ['Canal', 'Cumplimiento %']
        cumplimiento_canal = cumplimiento_canal.sort_values('Cumplimiento %', ascending=False)
        
        # Asignar color según semáforo
        def get_semaforo(valor):
            if valor >= 80:
                return "🟢", "Verde"
            elif valor >= 50:
                return "🟡", "Amarillo"
            else:
                return "🔴", "Rojo"
        
        cumplimiento_canal['Semáforo'], cumplimiento_canal['Estado'] = zip(*cumplimiento_canal['Cumplimiento %'].apply(get_semaforo))
        
        # Mostrar como tarjetas
        cols = st.columns(min(len(cumplimiento_canal), 4))
        
        for i, (_, row) in enumerate(cumplimiento_canal.iterrows()):
            col_idx = i % len(cols)
            with cols[col_idx]:
                color_fondo = "#d4edda" if row['Estado'] == "Verde" else "#fff3cd" if row['Estado'] == "Amarillo" else "#f8d7da"
                color_texto = "#155724" if row['Estado'] == "Verde" else "#856404" if row['Estado'] == "Amarillo" else "#721c24"
                
                st.markdown(f"""
                <div style="background-color:{color_fondo};padding:15px;border-radius:10px;text-align:center;border:2px solid {color_texto};margin:5px 0;">
                    <h3 style="margin:0;font-size:1.1rem;color:{color_texto};">{row['Canal']}</h3>
                    <h2 style="margin:5px 0;font-size:2rem;color:{color_texto};">{row['Semáforo']}</h2>
                    <p style="margin:0;font-size:1.5rem;font-weight:bold;color:{color_texto};">{row['Cumplimiento %']:.0f}%</p>
                    <p style="margin:5px 0 0 0;font-size:0.8rem;color:{color_texto};">{row['Estado']}</p>
                </div>
                """, unsafe_allow_html=True)
        
        # ===== ALERTA: Canales en ROJO =====
        canales_rojo = cumplimiento_canal[cumplimiento_canal['Estado'] == 'Rojo']
        if len(canales_rojo) > 0:
            st.error(f"🔴 **ALERTA:** {len(canales_rojo)} canal(es) en estado ROJO - {', '.join(canales_rojo['Canal'].tolist())}")
        
        canales_amarillo = cumplimiento_canal[cumplimiento_canal['Estado'] == 'Amarillo']
        if len(canales_amarillo) > 0:
            st.warning(f"🟡 **ATENCIÓN:** {len(canales_amarillo)} canal(es) en estado AMARILLO - {', '.join(canales_amarillo['Canal'].tolist())}")
        
        if len(canales_rojo) == 0 and len(canales_amarillo) == 0:
            st.success("🟢 **¡Todos los canales están en VERDE! Excelente desempeño.**")
    
    st.markdown("---")
    
    # ==================== GRÁFICOS PRINCIPALES ====================
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👤 Activaciones por Activador")
        if 'Activador de Marca' in df_filtrado.columns and len(df_filtrado) > 0:
            conteo_activadores = df_filtrado['Activador de Marca'].value_counts().reset_index()
            conteo_activadores.columns = ['Activador', 'Número']
            
            fig1 = px.bar(
                conteo_activadores,
                x='Activador',
                y='Número',
                color='Activador',
                text='Número',
                color_discrete_sequence=['#FF4B4B', '#4B9EFF']
            )
            fig1.update_traces(textposition='outside')
            fig1.update_layout(showlegend=False, height=350, xaxis_title="", yaxis_title="")
            st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        st.subheader("🏪 Activaciones por Canal")
        if 'Canal de Activación' in df_filtrado.columns and len(df_filtrado) > 0:
            conteo_canal = df_filtrado['Canal de Activación'].value_counts().reset_index()
            conteo_canal.columns = ['Canal', 'Número']
            
            fig2 = px.pie(
                conteo_canal,
                names='Canal',
                values='Número',
                color_discrete_sequence=px.colors.qualitative.Set3,
                hole=0.3
            )
            fig2.update_layout(height=350)
            st.plotly_chart(fig2, use_container_width=True)
    
    st.markdown("---")
    
    # ==================== VENTAS POR DÍA ====================
    if len(df_filtrado) > 0:
        st.subheader("📈 Tendencia de Ventas")
        
        if 'Fecha' in df_filtrado.columns and 'Ventas_netas_limpias' in df_filtrado.columns:
            ventas_por_dia = df_filtrado.groupby(df_filtrado['Fecha'].dt.date)['Ventas_netas_limpias'].sum().reset_index()
            ventas_por_dia.columns = ['Fecha', 'Ventas (kg)']
            ventas_por_dia = ventas_por_dia.dropna()
            ventas_por_dia = ventas_por_dia[ventas_por_dia['Ventas (kg)'] > 0]
            
            if len(ventas_por_dia) > 0:
                fig_ventas = px.line(
                    ventas_por_dia,
                    x='Fecha',
                    y='Ventas (kg)',
                    markers=True,
                    color_discrete_sequence=['#4B9EFF']
                )
                fig_ventas.update_layout(xaxis_title="", yaxis_title="Ventas (kg)", height=300)
                st.plotly_chart(fig_ventas, use_container_width=True)
            else:
                st.info("No hay datos de ventas para mostrar")
    
    st.markdown("---")
    
    # ==================== INCIDENCIAS ====================
    if len(df_filtrado) > 0:
        st.subheader("🛡️ Resumen de Incidencias")
        
        if 'Incidencias_detectadas' in df_filtrado.columns:
            incidencias_count = df_filtrado['Incidencias_detectadas'].value_counts().reset_index()
            incidencias_count.columns = ['Incidencia', 'Frecuencia']
            incidencias_count = incidencias_count[incidencias_count['Incidencia'] != 'Sin incidencias']
            
            if len(incidencias_count) > 0:
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    fig_incidencias = px.pie(
                        incidencias_count,
                        names='Incidencia',
                        values='Frecuencia',
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    fig_incidencias.update_layout(height=250)
                    st.plotly_chart(fig_incidencias, use_container_width=True)
                
                with col2:
                    for _, row in incidencias_count.iterrows():
                        st.markdown(f"**{row['Incidencia']}**: {row['Frecuencia']} casos")
                    
                    if '¿Se cumplió la meta?' in df_filtrado.columns:
                        blindadas = df_filtrado[
                            (df_filtrado['Incidencias_detectadas'] != 'Sin incidencias') & 
                            (df_filtrado['¿Se cumplió la meta?'] == 'Si')
                        ]
                        if len(blindadas) > 0:
                            st.success(f"🛡️ **{len(blindadas)} activaciones** con incidencias pero cumplieron la meta")
            else:
                st.success("✅ No se detectaron incidencias")
    
    st.markdown("---")
    
    # ==================== TABLA RESUMEN ====================
    with st.expander("📋 Ver detalle de activaciones"):
        columnas_mostrar = [
            'Fecha de Activación',
            'Activador de Marca',
            'Canal de Activación',
            'Lugar / Dirección del punto (ejm. PDV Cabaña, Asadero Sede 1 Suba, Jumbo 170, etc)',
            '¿Se cumplió la meta?',
            'Ventas_netas_limpias',
            'Incidencias_detectadas'
        ]
        
        columnas_existentes = [col for col in columnas_mostrar if col in df_filtrado.columns]
        
        if columnas_existentes:
            df_tabla = df_filtrado[columnas_existentes].copy()
            renombres = {
                'Fecha de Activación': '📅 Fecha',
                'Activador de Marca': '👤 Activador',
                'Canal de Activación': '🏪 Canal',
                'Lugar / Dirección del punto (ejm. PDV Cabaña, Asadero Sede 1 Suba, Jumbo 170, etc)': '📍 Ubicación',
                '¿Se cumplió la meta?': '✅ Meta',
                'Ventas_netas_limpias': '💰 Ventas (kg)',
                'Incidencias_detectadas': '⚠️ Incidencias'
            }
            df_tabla = df_tabla.rename(columns={k: v for k, v in renombres.items() if k in df_tabla.columns})
            
            st.dataframe(df_tabla, use_container_width=True, height=300)
    
    # ==================== PIE DE PÁGINA ====================
    st.markdown("---")
    st.caption(f"🔄 Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M')} | {len(df_filtrado)} activaciones mostradas")

else:
    st.error("❌ No se pudieron cargar los datos. Verifica la URL de Google Sheets.")
