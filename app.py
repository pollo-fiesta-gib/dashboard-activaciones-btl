import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import re
import calendar

# Configuración de la página
st.set_page_config(
    page_title="BTL Command Center", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal - MÁS SIMPLE
st.markdown("""
<div style="text-align: center; padding: 0.5rem 0;">
    <h1>🎯 Activaciones BTL - Pollo Fiesta</h1>
    <p style="color: #666; font-size: 0.95rem;">Resumen ejecutivo de activaciones</p>
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

def extraer_id_drive(url):
    if pd.isna(url) or not url:
        return None
    url = str(url)
    patrones = [
        r'[?&]id=([a-zA-Z0-9_-]+)',
        r'open\?id=([a-zA-Z0-9_-]+)',
        r'/d/([a-zA-Z0-9_-]+)'
    ]
    for patron in patrones:
        match = re.search(patron, url)
        if match:
            return match.group(1)
    return None

@st.cache_data(ttl=3600)
def cargar_datos():
    try:
        df = pd.read_csv(SHEET_URL)
        
        # Ventas
        col_ventas = 'Ventas netas aproximadas (en kilos, poner únicamente cifra)'
        if col_ventas in df.columns:
            df['Ventas_netas_limpias'] = df[col_ventas].apply(limpiar_ventas)
        else:
            for col in df.columns:
                if 'Ventas netas' in col or 'ventas' in col.lower():
                    df['Ventas_netas_limpias'] = df[col].apply(limpiar_ventas)
                    break
        
        # Ticket
        col_ticket = 'Ticket promedio estimado?'
        if col_ticket in df.columns:
            df['Ticket_limpo'] = df[col_ticket].apply(limpiar_ticket)
        else:
            for col in df.columns:
                if 'Ticket' in col or 'ticket' in col.lower():
                    df['Ticket_limpo'] = df[col].apply(limpiar_ticket)
                    break
        
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
            '🌡️ Clima': ['clima', 'frío', 'calor', 'temperatura'],
            '🏪 Competencia': ['competencia', 'competidor'],
            '👥 Poca afluencia': ['poca afluencia', 'poco público', 'baja afluencia'],
            '📦 Logística': ['inventario', 'pedido', 'llegó', 'retraso', 'demora'],
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
            df['Mes_num'] = df['Fecha'].dt.month
            df['Año'] = df['Fecha'].dt.year
        
        return df
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return None

# Cargar datos
df = cargar_datos()

if df is not None and len(df) > 0:
    
    # ==================== FILTROS SIMPLIFICADOS ====================
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
    st.markdown("## 📊 Resumen")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Activaciones", len(df_filtrado))
    
    with col2:
        if '¿Se cumplió la meta?' in df_filtrado.columns:
            cumplimiento = df_filtrado['¿Se cumplió la meta?'].value_counts(normalize=True).get('Si', 0) * 100
            st.metric("🎯 Cumplimiento", f"{cumplimiento:.0f}%")
        else:
            st.metric("🎯 Cumplimiento", "N/A")
    
    with col3:
        if 'Ventas_netas_limpias' in df_filtrado.columns:
            total_ventas = df_filtrado['Ventas_netas_limpias'].sum()
            if pd.notna(total_ventas) and total_ventas > 0:
                st.metric("💰 Ventas (kg)", f"{total_ventas:,.0f}")
            else:
                st.metric("💰 Ventas (kg)", "Sin datos")
        else:
            st.metric("💰 Ventas (kg)", "N/A")
    
    with col4:
        if 'Ticket_limpo' in df_filtrado.columns:
            ticket_promedio = df_filtrado['Ticket_limpo'].dropna()
            ticket_promedio = ticket_promedio[ticket_promedio > 0]
            if len(ticket_promedio) > 0:
                st.metric("💳 Ticket promedio", f"${ticket_promedio.mean():,.0f}")
            else:
                st.metric("💳 Ticket promedio", "Sin datos")
        else:
            st.metric("💳 Ticket promedio", "N/A")
    
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
                title="",
                color='Activador',
                text='Número',
                color_discrete_sequence=['#FF4B4B', '#4B9EFF']
            )
            fig1.update_traces(textposition='outside')
            fig1.update_layout(showlegend=False, height=300)
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
                title="",
                color_discrete_sequence=px.colors.qualitative.Set3,
                hole=0.3
            )
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)
    
    st.markdown("---")
    
    # ==================== CUMPLIMIENTO POR CANAL ====================
    st.subheader("📊 Cumplimiento de Meta por Canal")
    
    if 'Canal de Activación' in df_filtrado.columns and '¿Se cumplió la meta?' in df_filtrado.columns:
        cumplimiento_canal = df_filtrado.groupby('Canal de Activación')['¿Se cumplió la meta?'].value_counts().unstack().fillna(0)
        
        cumplimiento_canal['Total'] = cumplimiento_canal.sum(axis=1)
        for col in cumplimiento_canal.columns:
            if col != 'Total':
                cumplimiento_canal[f'{col}_%'] = (cumplimiento_canal[col] / cumplimiento_canal['Total'] * 100).round(1)
        
        if 'Si_%' in cumplimiento_canal.columns:
            cumplimiento_canal = cumplimiento_canal.sort_values('Si_%', ascending=False)
        
        st.dataframe(
            cumplimiento_canal,
            use_container_width=True,
            height=250,
            column_config={
                "Si_%": st.column_config.ProgressColumn(
                    "✅ Cumplió",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
                "No_%": st.column_config.ProgressColumn(
                    "❌ No cumplió",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
                "Parcialmente_%": st.column_config.ProgressColumn(
                    "🟡 Parcial",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                )
            }
        )
        
        if 'No' in cumplimiento_canal.columns and 'Total' in cumplimiento_canal.columns:
            canales_con_no = cumplimiento_canal[cumplimiento_canal['No'] > 0]
            if len(canales_con_no) > 0:
                st.warning(f"⚠️ **Canales con más 'No cumplimiento':** {', '.join(canales_con_no.index.tolist())}")
    
    st.markdown("---")
    
    # ==================== VENTAS POR DÍA ====================
    if len(df_filtrado) > 0:
        st.subheader("📈 Ventas por día")
        
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
                    title="",
                    markers=True,
                    color_discrete_sequence=['#4B9EFF']
                )
                fig_ventas.update_layout(xaxis_title="", yaxis_title="Ventas (kg)", height=300)
                st.plotly_chart(fig_ventas, use_container_width=True)
            else:
                st.info("No hay datos de ventas para mostrar")
    
    st.markdown("---")
    
    # ==================== BLINDAJE ====================
    if len(df_filtrado) > 0:
        st.subheader("🛡️ Incidencias detectadas")
        
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
                        title="",
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    fig_incidencias.update_layout(height=250)
                    st.plotly_chart(fig_incidencias, use_container_width=True)
                
                with col2:
                    for _, row in incidencias_count.iterrows():
                        st.markdown(f"**{row['Incidencia']}**: {row['Frecuencia']} casos")
                    
                    if '¿Se cumplió la meta?' in df_filtrado.columns:
                        blindadas = df_filtrado[(df_filtrado['Incidencias_detectadas'] != 'Sin incidencias') & (df_filtrado['¿Se cumplió la meta?'] == 'Si')]
                        if len(blindadas) > 0:
                            st.success(f"🛡️ **{len(blindadas)} activaciones** tuvieron incidencias pero cumplieron la meta")
            else:
                st.success("✅ No se detectaron incidencias")
    
    st.markdown("---")
    
    # ==================== VISOR DE FOTOS CORREGIDO ====================
    if len(df_filtrado) > 0:
        st.subheader("📸 Ver evidencia en campo")
        
        col_foto = None
        col_firma = None
        
        for col in df_filtrado.columns:
            if 'Foto' in col and ('lineal' in col.lower() or 'vitrina' in col.lower()):
                col_foto = col
            if 'Firma' in col:
                col_firma = col
        
        # Preparar opciones usando el índice real de pandas
        opciones = []
        for idx in df_filtrado.index:
            row = df_filtrado.loc[idx]
            fecha = row.get('Fecha de Activación', 'Sin fecha')
            activador = row.get('Activador de Marca', 'Sin activador')
            lugar = row.get('Lugar / Dirección del punto (ejm. PDV Cabaña, Asadero Sede 1 Suba, Jumbo 170, etc)', 'Sin lugar')
            if len(str(lugar)) > 30:
                lugar = str(lugar)[:30] + "..."
            opciones.append(f"{fecha} | {activador} | {lugar}")
        
        if opciones:
            seleccion_idx = st.selectbox(
                "Selecciona una activación:",
                options=range(len(opciones)),
                format_func=lambda i: opciones[i]
            )
            
            if seleccion_idx is not None:
                idx_real = df_filtrado.index[seleccion_idx]
                row = df_filtrado.loc[idx_real]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📸 Foto del Lineal**")
                    if col_foto and col_foto in row and pd.notna(row[col_foto]):
                        url_foto = row[col_foto]
                        file_id = extraer_id_drive(url_foto)
                        if file_id:
                            link = f"https://drive.google.com/open?id={file_id}"
                            st.markdown(f"""
                            <div style="background:#f0f2f6;padding:12px;border-radius:8px;text-align:center;">
                                <a href="{link}" target="_blank" style="background:#FF4B4B;color:white;padding:8px 20px;border-radius:5px;text-decoration:none;display:inline-block;">
                                    📷 Ver foto en Drive
                                </a>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"[Ver foto]({url_foto})")
                    else:
                        st.info("📷 No hay foto disponible")
                
                with col2:
                    st.markdown("**✍️ Firma del Administrador**")
                    if col_firma and col_firma in row and pd.notna(row[col_firma]):
                        url_firma = row[col_firma]
                        file_id = extraer_id_drive(url_firma)
                        if file_id:
                            link = f"https://drive.google.com/open?id={file_id}"
                            st.markdown(f"""
                            <div style="background:#f0f2f6;padding:12px;border-radius:8px;text-align:center;">
                                <a href="{link}" target="_blank" style="background:#4B9EFF;color:white;padding:8px 20px;border-radius:5px;text-decoration:none;display:inline-block;">
                                    📝 Ver firma en Drive
                                </a>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"[Ver firma]({url_firma})")
                    else:
                        st.info("✍️ No hay firma disponible")
    
    # ==================== TABLA COMPLETA ====================
    if len(df_filtrado) > 0:
        with st.expander("📋 Ver tabla completa de activaciones"):
            columnas_mostrar = [
                'Fecha de Activación',
                'Activador de Marca',
                'Canal de Activación',
                'Lugar / Dirección del punto (ejm. PDV Cabaña, Asadero Sede 1 Suba, Jumbo 170, etc)',
                '¿Se cumplió la meta?',
                'Ventas_netas_limpias',
                'Ticket_limpo',
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
                    'Ticket_limpo': '💳 Ticket ($)',
                    'Incidencias_detectadas': '⚠️ Incidencias'
                }
                df_tabla = df_tabla.rename(columns={k: v for k, v in renombres.items() if k in df_tabla.columns})
                
                st.dataframe(df_tabla, use_container_width=True, height=300)
    
    # ==================== PIE DE PÁGINA ====================
    st.markdown("---")
    st.caption(f"🔄 Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M')} | {len(df_filtrado)} activaciones mostradas")

else:
    st.error("❌ No se pudieron cargar los datos. Verifica la URL de Google Sheets.")
    st.info("Asegúrate de que el archivo esté compartido como 'Cualquier persona con el enlace puede ver'")
