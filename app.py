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
<div style="text-align: center; padding: 1rem 0;">
    <h1>🎯 Centro de Control - Activaciones Pollo Fiesta</h1>
    <p style="color: #666; font-size: 1.1rem;">Monitoreo en tiempo real de activaciones BTL</p>
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

def convertir_link_google_drive(url):
    """Convierte un link de Google Drive a formato embed o lo deja como está"""
    if pd.isna(url) or not url:
        return None
    url = str(url)
    
    # Si ya es un link de vista previa, dejarlo
    if 'uc?export=view' in url or 'thumbnail' in url:
        return url
    
    # Buscar el ID del archivo
    patrones = [
        r'[?&]id=([a-zA-Z0-9_-]+)',
        r'open\?id=([a-zA-Z0-9_-]+)',
        r'/d/([a-zA-Z0-9_-]+)'
    ]
    for patron in patrones:
        match = re.search(patron, url)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?export=view&id={file_id}"
    
    # Si no se pudo extraer ID, devolver el link original
    return url

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
            '🌡️ Clima adverso': ['clima', 'frío', 'calor', 'temperatura'],
            '🏪 Competencia': ['competencia', 'competidor'],
            '👥 Poca afluencia': ['poca afluencia', 'poco público', 'baja afluencia'],
            '📦 Problemas logísticos': ['inventario', 'pedido', 'llegó', 'retraso', 'demora'],
            '🔧 Problemas técnicos': ['nevera', 'falla', 'técnica']
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
        
        # Procesar links de fotos para que sean clickeables
        for col in df.columns:
            if 'Foto' in col and 'lineal' in col.lower():
                df[col + '_link'] = df[col].apply(convertir_link_google_drive)
            if 'Firma' in col:
                df[col + '_link'] = df[col].apply(convertir_link_google_drive)
        
        return df
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return None

# Cargar datos
df = cargar_datos()

if df is not None and len(df) > 0:
    st.success(f"✅ Datos cargados correctamente - {len(df)} activaciones registradas")
    
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
        
        if 'Fecha' in df.columns and len(df) > 0:
            fecha_min = df['Fecha'].min().date()
            fecha_max = df['Fecha'].max().date()
            fecha_inicio = st.date_input("📅 Desde", fecha_min, min_value=fecha_min, max_value=fecha_max)
            fecha_fin = st.date_input("📅 Hasta", fecha_max, min_value=fecha_min, max_value=fecha_max)
        else:
            fecha_inicio = None
            fecha_fin = None
        
        st.markdown("---")
        st.info(f"📊 Mostrando {len(df)} activaciones totales")
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    if activador_seleccionado != 'Todos' and 'Activador de Marca' in df.columns:
        df_filtrado = df_filtrado[df_filtrado['Activador de Marca'] == activador_seleccionado]
    
    if canal_seleccionado != 'Todos' and 'Canal de Activación' in df.columns:
        df_filtrado = df_filtrado[df_filtrado['Canal de Activación'] == canal_seleccionado]
    
    if fecha_inicio and fecha_fin and 'Fecha' in df_filtrado.columns:
        df_filtrado = df_filtrado[
            (df_filtrado['Fecha'].dt.date >= fecha_inicio) & 
            (df_filtrado['Fecha'].dt.date <= fecha_fin)
        ]
    
    # ==================== KPIs ====================
    st.markdown("## 📊 Resumen Ejecutivo")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📊 Total Activaciones", len(df_filtrado))
    
    with col2:
        if '¿Se cumplió la meta?' in df_filtrado.columns:
            cumplimiento = df_filtrado['¿Se cumplió la meta?'].value_counts(normalize=True).get('Si', 0) * 100
            st.metric("🎯 Cumplimiento Meta", f"{cumplimiento:.0f}%")
        else:
            st.metric("🎯 Cumplimiento Meta", "N/A")
    
    with col3:
        if 'Activador de Marca' in df_filtrado.columns:
            st.metric("👤 Activadores", df_filtrado['Activador de Marca'].nunique())
        else:
            st.metric("👤 Activadores", "N/A")
    
    with col4:
        if 'Canal de Activación' in df_filtrado.columns:
            st.metric("🏪 Canales", df_filtrado['Canal de Activación'].nunique())
        else:
            st.metric("🏪 Canales", "N/A")
    
    with col5:
        if 'Ventas_netas_limpias' in df_filtrado.columns:
            total_ventas = df_filtrado['Ventas_netas_limpias'].sum()
            if pd.notna(total_ventas) and total_ventas > 0:
                st.metric("💰 Ventas Totales (kg)", f"{total_ventas:,.0f}")
            else:
                st.metric("💰 Ventas Totales", "Sin datos")
        else:
            st.metric("💰 Ventas Totales", "N/A")
    
    st.markdown("---")
    
    # ==================== GRÁFICOS PRINCIPALES ====================
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Activaciones por Activador")
        if 'Activador de Marca' in df_filtrado.columns and len(df_filtrado) > 0:
            conteo_activadores = df_filtrado['Activador de Marca'].value_counts().reset_index()
            conteo_activadores.columns = ['Activador', 'Número de Activaciones']
            
            fig1 = px.bar(
                conteo_activadores,
                x='Activador',
                y='Número de Activaciones',
                title="Número de activaciones por activador",
                color='Activador',
                text='Número de Activaciones',
                color_discrete_sequence=['#FF4B4B', '#4B9EFF']
            )
            fig1.update_traces(textposition='outside')
            fig1.update_layout(showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No hay datos disponibles")
    
    with col2:
        st.subheader("🏪 Activaciones por Canal")
        if 'Canal de Activación' in df_filtrado.columns and len(df_filtrado) > 0:
            conteo_canal = df_filtrado['Canal de Activación'].value_counts().reset_index()
            conteo_canal.columns = ['Canal', 'Número de Activaciones']
            
            fig2 = px.pie(
                conteo_canal,
                names='Canal',
                values='Número de Activaciones',
                title="Distribución por canal",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No hay datos disponibles")
    
    # ==================== GRÁFICOS ADICIONALES (SIN MAPA) ====================
    if len(df_filtrado) > 0:
        st.markdown("---")
        st.subheader("📈 Análisis de Desempeño")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Ventas por día")
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
                        title="Evolución de ventas por día",
                        markers=True,
                        color_discrete_sequence=['#4B9EFF']
                    )
                    fig_ventas.update_layout(xaxis_title="Fecha", yaxis_title="Ventas (kg)")
                    st.plotly_chart(fig_ventas, use_container_width=True)
                else:
                    st.info("No hay datos de ventas para mostrar")
            else:
                st.info("Datos de ventas no disponibles")
        
        with col2:
            st.markdown("#### 💰 Ticket Promedio")
            if 'Ticket_limpo' in df_filtrado.columns:
                tickets = df_filtrado['Ticket_limpo'].dropna()
                tickets = tickets[tickets > 0]
                
                if len(tickets) > 0:
                    fig_ticket = px.box(
                        y=tickets,
                        title="Distribución del Ticket Promedio",
                        labels={'y': 'Ticket Promedio ($)'},
                        color_discrete_sequence=['#FF4B4B']
                    )
                    fig_ticket.update_layout(yaxis_title="Ticket Promedio ($)")
                    st.plotly_chart(fig_ticket, use_container_width=True)
                else:
                    st.info("No hay datos de ticket promedio para mostrar")
            else:
                st.info("Datos de ticket promedio no disponibles")
    
    # ==================== ANÁLISIS DE CUMPLIMIENTO ====================
    if len(df_filtrado) > 0:
        st.markdown("---")
        st.subheader("📊 Análisis de Cumplimiento de Meta")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if '¿Se cumplió la meta?' in df_filtrado.columns:
                cumplimiento_counts = df_filtrado['¿Se cumplió la meta?'].value_counts().reset_index()
                cumplimiento_counts.columns = ['Estado', 'Cantidad']
                
                fig3 = px.pie(
                    cumplimiento_counts,
                    names='Estado',
                    values='Cantidad',
                    title="Cumplimiento de Meta",
                    color='Estado',
                    color_discrete_map={
                        'Si': '#2ecc71', 
                        'No': '#e74c3c', 
                        'Parcialmente': '#f39c12'
                    }
                )
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No hay datos de cumplimiento disponibles")
        
        with col2:
            if 'Canal de Activación' in df_filtrado.columns and '¿Se cumplió la meta?' in df_filtrado.columns:
                cumplimiento_canal = df_filtrado.groupby('Canal de Activación')['¿Se cumplió la meta?'].apply(
                    lambda x: (x == 'Si').sum() / len(x) * 100
                ).reset_index()
                cumplimiento_canal.columns = ['Canal', '% Cumplimiento']
                cumplimiento_canal = cumplimiento_canal.sort_values('% Cumplimiento', ascending=False)
                
                fig4 = px.bar(
                    cumplimiento_canal,
                    x='Canal',
                    y='% Cumplimiento',
                    title="% Cumplimiento por Canal",
                    color='Canal',
                    text='% Cumplimiento',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig4.update_traces(textposition='outside', texttemplate='%{text:.1f}%')
                fig4.update_layout(yaxis_range=[0, 100], showlegend=False)
                st.plotly_chart(fig4, use_container_width=True)
            else:
                st.info("No hay datos de cumplimiento por canal disponibles")
    
    # ==================== BLINDAJE ====================
    if len(df_filtrado) > 0:
        st.markdown("---")
        st.subheader("🛡️ Análisis de Incidencias (Blindaje)")
        
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
                        title="Distribución de Incidencias",
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    st.plotly_chart(fig_incidencias, use_container_width=True)
                
                with col2:
                    st.markdown("#### 📋 Activaciones con Incidencias")
                    
                    columnas_disponibles = [
                        'Fecha de Activación', 
                        'Activador de Marca', 
                        'Canal de Activación', 
                        'Lugar / Dirección del punto (ejm. PDV Cabaña, Asadero Sede 1 Suba, Jumbo 170, etc)',
                        '¿Se cumplió la meta?', 
                        'Incidencias_detectadas'
                    ]
                    columnas_existentes = [col for col in columnas_disponibles if col in df_filtrado.columns]
                    
                    if columnas_existentes:
                        df_incidencias_detalle = df_filtrado[df_filtrado['Incidencias_detectadas'] != 'Sin incidencias'][columnas_existentes].copy()
                        
                        if len(df_incidencias_detalle) > 0:
                            st.dataframe(
                                df_incidencias_detalle, 
                                use_container_width=True,
                                height=300
                            )
                            
                            if '¿Se cumplió la meta?' in df_incidencias_detalle.columns:
                                blindadas = df_incidencias_detalle[df_incidencias_detalle['¿Se cumplió la meta?'] == 'Si']
                                if len(blindadas) > 0:
                                    st.success(f"🛡️ {len(blindadas)} activaciones tuvieron incidencias pero cumplieron la meta - ¡Activadores blindados!")
            else:
                st.success("✅ No se detectaron incidencias en las activaciones")
    
    # ==================== VISOR DE FOTOS MEJORADO ====================
    if len(df_filtrado) > 0:
        st.markdown("---")
        st.subheader("📸 Visor de Fotos - Evidencia en Campo")
        
        # Encontrar las columnas de fotos y firmas
        col_foto = None
        col_firma = None
        
        for col in df_filtrado.columns:
            if 'Foto' in col and ('lineal' in col.lower() or 'vitrina' in col.lower()):
                col_foto = col
            if 'Firma' in col:
                col_firma = col
        
        # Preparar opciones
        opciones = []
        indices = []
        for idx, row in df_filtrado.iterrows():
            fecha = row.get('Fecha de Activación', 'Sin fecha')
            activador = row.get('Activador de Marca', 'Sin activador')
            lugar = row.get('Lugar / Dirección del punto (ejm. PDV Cabaña, Asadero Sede 1 Suba, Jumbo 170, etc)', 'Sin lugar')
            if len(str(lugar)) > 40:
                lugar = str(lugar)[:40] + "..."
            opciones.append(f"📅 {fecha} | 👤 {activador} | 📍 {lugar}")
            indices.append(idx)
        
        if opciones:
            seleccion_idx = st.selectbox(
                "Selecciona una activación para ver las fotos:",
                options=range(len(opciones)),
                format_func=lambda i: opciones[i]
            )
            
            if seleccion_idx is not None:
                idx = indices[seleccion_idx]
                row = df_filtrado.iloc[idx]
                
                # Mostrar enlaces a las fotos
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📸 Foto del Lineal o Vitrina**")
                    if col_foto and col_foto in row and pd.notna(row[col_foto]):
                        url_foto = row[col_foto]
                        # Intentar convertir a formato embed
                        url_embed = convertir_link_google_drive(url_foto)
                        # Mostrar como enlace clickeable
                        st.markdown(f"""
                        <div style="background-color: #f0f2f6; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #ddd;">
                            <p style="font-size: 14px; color: #666;">🖼️ Haz clic en el botón para ver la foto</p>
                            <a href="{url_foto}" target="_blank" style="display: inline-block; background-color: #FF4B4B; color: white; padding: 10px 25px; border-radius: 5px; text-decoration: none; font-weight: bold;">
                                📷 Ver foto en Google Drive
                            </a>
                            <p style="font-size: 12px; color: #999; margin-top: 8px;">Se abrirá en una nueva pestaña</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("📷 No hay foto disponible para esta activación")
                
                with col2:
                    st.markdown("**✍️ Firma del Administrador**")
                    if col_firma and col_firma in row and pd.notna(row[col_firma]):
                        url_firma = row[col_firma]
                        st.markdown(f"""
                        <div style="background-color: #f0f2f6; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #ddd;">
                            <p style="font-size: 14px; color: #666;">✍️ Haz clic en el botón para ver la firma</p>
                            <a href="{url_firma}" target="_blank" style="display: inline-block; background-color: #4B9EFF; color: white; padding: 10px 25px; border-radius: 5px; text-decoration: none; font-weight: bold;">
                                📝 Ver firma en Google Drive
                            </a>
                            <p style="font-size: 12px; color: #999; margin-top: 8px;">Se abrirá en una nueva pestaña</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("✍️ No hay firma disponible para esta activación")
                
                # Detalles de la activación
                with st.expander("📋 Ver detalles completos de la activación"):
                    detalles = {
                        'Campo': ['Activador', 'Canal', 'Ubicación', 'Fecha', 'Cumplió meta', 'Ventas (kg)', 'Ticket promedio', 'Incidencias'],
                        'Valor': [
                            row.get('Activador de Marca', 'N/A'),
                            row.get('Canal de Activación', 'N/A'),
                            row.get('Lugar / Dirección del punto (ejm. PDV Cabaña, Asadero Sede 1 Suba, Jumbo 170, etc)', 'N/A'),
                            row.get('Fecha de Activación', 'N/A'),
                            row.get('¿Se cumplió la meta?', 'N/A'),
                            f"{row.get('Ventas_netas_limpias', 'N/A')} kg" if pd.notna(row.get('Ventas_netas_limpias', None)) else 'N/A',
                            f"${row.get('Ticket_limpo', 'N/A'):,.0f}" if pd.notna(row.get('Ticket_limpo', None)) else 'N/A',
                            row.get('Incidencias_detectadas', 'Sin incidencias')
                        ]
                    }
                    df_detalles = pd.DataFrame(detalles)
                    st.dataframe(df_detalles, use_container_width=True, hide_index=True)
        else:
            st.info("No hay activaciones disponibles para mostrar")
    
    # ==================== TABLA COMPLETA ====================
    if len(df_filtrado) > 0:
        st.markdown("---")
        st.subheader("📋 Tabla Completa de Activaciones")
        
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
            
            st.dataframe(
                df_tabla, 
                use_container_width=True, 
                height=400
            )
        else:
            st.dataframe(df_filtrado, use_container_width=True, height=400)
    
    # ==================== PIE DE PÁGINA ====================
    st.markdown("---")
    st.caption(f"🔄 Actualizado automáticamente desde Google Forms - Última carga: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if len(df_filtrado) > 0:
        st.caption(f"📊 Total de registros: {len(df)} - Filtrados: {len(df_filtrado)}")

else:
    st.error("❌ No se pudieron cargar los datos. Verifica la URL de Google Sheets.")
    st.info("Asegúrate de que el archivo esté compartido como 'Cualquier persona con el enlace puede ver'")
