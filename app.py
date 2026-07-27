import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import re

# Configuración de la página - MEJORADA
st.set_page_config(
    page_title="BTL Command Center", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal con mejor estilo
st.markdown("""
<div style="text-align: center; padding: 1rem 0;">
    <h1>🎯 Centro de Control - Activaciones Pollo Fiesta</h1>
    <p style="color: #666; font-size: 1.1rem;">Monitoreo en tiempo real de activaciones BTL</p>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# 🔴 URL de tu Google Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/1fFcgK4ikmaEDXXesAc7wljONAyYx0b-0DAhjGa4vZqg/export?format=csv"

# Funciones de limpieza MEJORADAS
def limpiar_ventas(valor):
    """Extrae números de strings como '150 kls', '80 kl', etc."""
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor) if valor > 0 else None
    if isinstance(valor, str):
        # Buscar números en el string
        numeros = re.findall(r'[\d,]+', valor)
        if numeros:
            try:
                return float(numeros[0].replace(',', ''))
            except:
                return None
    return None

def limpiar_ticket(valor):
    """Limpia valores de ticket promedio."""
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor) if valor > 0 else None
    if isinstance(valor, str):
        # Limpiar caracteres no numéricos
        limpio = re.sub(r'[^\d,]', '', valor)
        if limpio:
            try:
                return float(limpio.replace(',', ''))
            except:
                return None
    return None

def extraer_nombre_lugar(direccion):
    """Extrae el nombre del lugar de la dirección."""
    if pd.isna(direccion):
        return "Ubicación no especificada"
    direccion = str(direccion)
    # Buscar palabras clave
    lugares = ['Jumbo', 'Metro', 'PDV', 'Merkacol', 'Supertiendas', 'Plaza', 'Camacho', 'Avicola']
    for lugar in lugares:
        if lugar.lower() in direccion.lower():
            return lugar
    # Si hay dirección larga, tomar los primeros 30 caracteres
    if len(direccion) > 30:
        return direccion[:30] + "..."
    return direccion

def extraer_ubicacion_para_mapa(direccion):
    """Extrae el nombre de la ubicación para el mapa."""
    if pd.isna(direccion):
        return "Desconocido"
    direccion = str(direccion).lower()
    ubicaciones = {
        'suba': 'Suba',
        'engativa': 'Engativa',
        'kennedy': 'Kennedy',
        'soacha': 'Soacha',
        'tunja': 'Tunja',
        'fusagasuga': 'Fusagasuga',
        'bosa': 'Bosa',
        'santa fe': 'Santa Fe',
        'toberin': 'Toberin',
        'cabaña': 'Cabaña',
        'pradera': 'Pradera',
        'floresta': 'Floresta',
        'abastos': 'Abastos',
        'hayuelos': 'Hayuelos',
        'altos del country': 'Altos del Country',
        '20 de julio': '20 de Julio',
        'santa ana': 'Santa Ana',
        'tintal': 'Tintal',
        'banderas': 'Banderas',
        'suba rincon': 'Suba Rincón',
        'floresta': 'Floresta',
        'sogamoso': 'Sogamoso',
        'chiquinquira': 'Chiquinquirá',
        'la calera': 'La Calera',
        'el rosal': 'El Rosal'
    }
    for key, value in ubicaciones.items():
        if key in direccion:
            return value
    return "Bogotá"  # Valor por defecto

def convertir_fecha_segura(fecha_str):
    """Convierte fechas de forma segura."""
    if pd.isna(fecha_str):
        return pd.NaT
    try:
        return pd.to_datetime(fecha_str, errors='coerce')
    except:
        return pd.NaT

def extraer_id_drive(url):
    """Extrae el ID de un link de Google Drive."""
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
        
        # Limpiar ventas
        if 'Ventas netas aproximadas' in df.columns:
            df['Ventas_netas_limpias'] = df['Ventas netas aproximadas'].apply(limpiar_ventas)
        
        # Limpiar ticket
        if 'Ticket promedio estimado' in df.columns:
            df['Ticket_limpo'] = df['Ticket promedio estimado'].apply(limpiar_ticket)
        
        # Extraer ubicación para el mapa
        if 'Lugar / Dirección del punto' in df.columns:
            df['Ubicacion_mapa'] = df['Lugar / Dirección del punto'].apply(extraer_ubicacion_para_mapa)
            df['Lugar_nombre'] = df['Lugar / Dirección del punto'].apply(extraer_nombre_lugar)
        
        # Detectar incidencias
        columnas_incidencias = [
            'Observaciones del estado inicial',
            '¿Alguna novedad relevante durante la activación?',
            'Oportunidades de mejora para próxima activación'
        ]
        
        df['Texto_completo'] = ''
        for col in columnas_incidencias:
            if col in df.columns:
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
        if 'Fecha de Activación' in df.columns:
            df['Fecha'] = df['Fecha de Activación'].apply(convertir_fecha_segura)
            df = df.dropna(subset=['Fecha'])
        
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
        
        # Filtro de activador
        if 'Activador de Marca' in df.columns:
            activadores = ['Todos'] + list(df['Activador de Marca'].unique())
            activador_seleccionado = st.selectbox("👤 Activador", activadores)
        else:
            activador_seleccionado = 'Todos'
        
        # Filtro de canal
        if 'Canal de Activación' in df.columns:
            canales = ['Todos'] + list(df['Canal de Activación'].unique())
            canal_seleccionado = st.selectbox("🏪 Canal", canales)
        else:
            canal_seleccionado = 'Todos'
        
        # Filtro de fecha
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
    
    # ==================== KPIs MEJORADOS ====================
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
    
    # ==================== MAPA DE ACTIVACIONES CORREGIDO ====================
    if len(df_filtrado) > 0:
        st.markdown("---")
        st.subheader("📍 Mapa de Activaciones")
        
        if 'Ubicacion_mapa' in df_filtrado.columns:
            # Coordenadas de ubicaciones en Bogotá
            coordenadas = {
                'Suba': {'lat': 4.7407, 'lon': -74.0830},
                'Engativa': {'lat': 4.7000, 'lon': -74.1000},
                'Kennedy': {'lat': 4.6600, 'lon': -74.1500},
                'Soacha': {'lat': 4.5800, 'lon': -74.2200},
                'Tunja': {'lat': 5.5300, 'lon': -73.3600},
                'Fusagasuga': {'lat': 4.3400, 'lon': -74.3600},
                'Bosa': {'lat': 4.6100, 'lon': -74.1900},
                'Santa Fe': {'lat': 4.6100, 'lon': -74.0700},
                'Toberin': {'lat': 4.6600, 'lon': -74.1300},
                'Cabaña': {'lat': 4.7000, 'lon': -74.0800},
                'Pradera': {'lat': 4.6700, 'lon': -74.1200},
                'Floresta': {'lat': 4.6800, 'lon': -74.0900},
                'Abastos': {'lat': 4.6500, 'lon': -74.1100},
                'Hayuelos': {'lat': 4.7200, 'lon': -74.1600},
                'Altos del Country': {'lat': 4.7100, 'lon': -74.0300},
                'Bogotá': {'lat': 4.7110, 'lon': -74.0721},
                '20 de Julio': {'lat': 4.6200, 'lon': -74.1100},
                'Santa Ana': {'lat': 4.6900, 'lon': -74.0700},
                'Tintal': {'lat': 4.6800, 'lon': -74.1800},
                'Banderas': {'lat': 4.7000, 'lon': -74.1200},
                'Suba Rincón': {'lat': 4.7500, 'lon': -74.0900},
                'Sogamoso': {'lat': 5.5300, 'lon': -73.3600},
                'Chiquinquirá': {'lat': 5.6300, 'lon': -73.8200},
                'La Calera': {'lat': 4.7200, 'lon': -73.9800},
                'El Rosal': {'lat': 4.8500, 'lon': -74.2600}
            }
            
            # Asignar coordenadas
            df_filtrado['Latitud'] = 4.7110
            df_filtrado['Longitud'] = -74.0721
            
            for ubicacion, coords in coordenadas.items():
                mascara = df_filtrado['Ubicacion_mapa'] == ubicacion
                if mascara.sum() > 0:
                    df_filtrado.loc[mascara, 'Latitud'] = coords['lat']
                    df_filtrado.loc[mascara, 'Longitud'] = coords['lon']
            
            # Crear mapa con Plotly
            color_col = 'Activador de Marca' if 'Activador de Marca' in df_filtrado.columns else None
            hover_data = {
                'Ubicacion_mapa': True,
                'Lugar / Dirección del punto': True,
                'Canal de Activación': True,
                '¿Se cumplió la meta?': True
            }
            hover_data = {k: v for k, v in hover_data.items() if k in df_filtrado.columns}
            
            fig_mapa = px.scatter_mapbox(
                df_filtrado,
                lat="Latitud",
                lon="Longitud",
                hover_name=color_col if color_col else None,
                hover_data=hover_data if hover_data else None,
                color=color_col if color_col else None,
                size=[15] * len(df_filtrado),
                zoom=9,
                title="Ubicación de activaciones en Bogotá y alrededores",
                color_discrete_sequence=['#FF4B4B', '#4B9EFF'] if color_col else None
            )
            
            fig_mapa.update_layout(
                mapbox_style="open-street-map",
                height=500,
                margin=dict(l=0, r=0, t=50, b=0)
            )
            
            st.plotly_chart(fig_mapa, use_container_width=True)
            
            # Mostrar tabla de ubicaciones
            with st.expander("📍 Ver detalle de ubicaciones"):
                ubicaciones_counts = df_filtrado['Ubicacion_mapa'].value_counts().reset_index()
                ubicaciones_counts.columns = ['Ubicación', 'Número de activaciones']
                st.dataframe(ubicaciones_counts, use_container_width=True)
        else:
            st.info("No hay datos de ubicación disponibles para el mapa")
    
    # ==================== GRÁFICOS ADICIONALES ====================
    if len(df_filtrado) > 0:
        st.markdown("---")
        st.subheader("📈 Análisis de Desempeño")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Ventas por día")
            if 'Fecha' in df_filtrado.columns and 'Ventas_netas_limpias' in df_filtrado.columns:
                # Agrupar por fecha
                ventas_por_dia = df_filtrado.groupby(df_filtrado['Fecha'].dt.date)['Ventas_netas_limpias'].sum().reset_index()
                ventas_por_dia.columns = ['Fecha', 'Ventas (kg)']
                
                # Filtrar valores nulos y cero
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
                    
                    # Mostrar estadísticas adicionales
                    col1a, col1b, col1c = st.columns(3)
                    with col1a:
                        st.metric("📈 Promedio diario", f"{ventas_por_dia['Ventas (kg)'].mean():.0f} kg")
                    with col1b:
                        st.metric("📊 Máximo diario", f"{ventas_por_dia['Ventas (kg)'].max():.0f} kg")
                    with col1c:
                        st.metric("📉 Mínimo diario", f"{ventas_por_dia['Ventas (kg)'].min():.0f} kg")
                else:
                    st.info("No hay datos de ventas para mostrar")
            else:
                st.info("Datos de ventas no disponibles")
        
        with col2:
            st.markdown("#### 💰 Ticket Promedio")
            if 'Ticket_limpo' in df_filtrado.columns:
                # Filtrar valores válidos
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
                    
                    # Mostrar estadísticas adicionales
                    col2a, col2b, col2c = st.columns(3)
                    with col2a:
                        st.metric("💰 Promedio", f"${tickets.mean():,.0f}")
                    with col2b:
                        st.metric("📊 Mediana", f"${tickets.median():,.0f}")
                    with col2c:
                        st.metric("📈 Máximo", f"${tickets.max():,.0f}")
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
                # Contar valores
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
                # Calcular % cumplimiento por canal
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
    
    # ==================== BLINDAJE AVANZADO ====================
    if len(df_filtrado) > 0:
        st.markdown("---")
        st.subheader("🛡️ Análisis de Incidencias (Blindaje)")
        
        if 'Incidencias_detectadas' in df_filtrado.columns:
            # Contar incidencias
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
                    
                    # Columnas disponibles
                    columnas_disponibles = [
                        'Fecha de Activación', 
                        'Activador de Marca', 
                        'Canal de Activación', 
                        'Lugar / Dirección del punto', 
                        '¿Se cumplió la meta?', 
                        'Incidencias_detectadas'
                    ]
                    columnas_existentes = [col for col in columnas_disponibles if col in df_filtrado.columns]
                    
                    if columnas_existentes:
                        df_incidencias_detalle = df_filtrado[df_filtrado['Incidencias_detectadas'] != 'Sin incidencias'][columnas_existentes].copy()
                        
                        if len(df_incidencias_detalle) > 0:
                            # Mostrar tabla con colores
                            st.dataframe(
                                df_incidencias_detalle, 
                                use_container_width=True,
                                height=300,
                                column_config={
                                    "Incidencias_detectadas": "⚠️ Incidencias",
                                    "¿Se cumplió la meta?": "✅ Meta"
                                }
                            )
                            
                            # Contar blindados
                            if '¿Se cumplió la meta?' in df_incidencias_detalle.columns:
                                blindadas = df_incidencias_detalle[df_incidencias_detalle['¿Se cumplió la meta?'] == 'Si']
                                if len(blindadas) > 0:
                                    st.success(f"🛡️ {len(blindadas)} activaciones tuvieron incidencias pero cumplieron la meta - ¡Activadores blindados!")
                                
                                no_cumplidas = df_incidencias_detalle[df_incidencias_detalle['¿Se cumplió la meta?'] != 'Si']
                                if len(no_cumplidas) > 0:
                                    st.warning(f"⚠️ {len(no_cumplidas)} activaciones tuvieron incidencias y NO cumplieron la meta - Revisar apoyo")
            else:
                st.success("✅ No se detectaron incidencias en las activaciones")
    
    # ==================== VISOR DE FOTOS CORREGIDO ====================
    if len(df_filtrado) > 0:
        st.markdown("---")
        st.subheader("📸 Visor de Fotos - Evidencia en Campo")
        
        # Preparar opciones con mejor formato
        opciones = []
        indices = []
        for idx, row in df_filtrado.iterrows():
            fecha = row.get('Fecha de Activación', 'Sin fecha')
            activador = row.get('Activador de Marca', 'Sin activador')
            lugar = row.get('Lugar / Dirección del punto', 'Sin lugar')
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
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📸 Foto del Lineal o Vitrina**")
                    url_foto = row.get('Foto del lineal o vitrina (obligatoria)', '')
                    if pd.notna(url_foto) and url_foto:
                        # Intentar obtener el ID de Google Drive
                        file_id = extraer_id_drive(url_foto)
                        if file_id:
                            # Mostrar como imagen embed
                            embed_url = f"https://drive.google.com/uc?export=view&id={file_id}"
                            try:
                                st.image(embed_url, use_container_width=True)
                            except:
                                st.markdown(f"🔗 [Ver foto en Google Drive]({url_foto})")
                        else:
                            # Mostrar como enlace
                            st.markdown(f"🔗 [Ver foto en Google Drive]({url_foto})")
                    else:
                        st.info("📷 No hay foto disponible")
                
                with col2:
                    st.markdown("**✍️ Firma del Administrador**")
                    url_firma = row.get('Firma de quien califica', '')
                    if pd.notna(url_firma) and url_firma:
                        file_id = extraer_id_drive(url_firma)
                        if file_id:
                            embed_url = f"https://drive.google.com/uc?export=view&id={file_id}"
                            try:
                                st.image(embed_url, use_container_width=True)
                            except:
                                st.markdown(f"🔗 [Ver firma en Google Drive]({url_firma})")
                        else:
                            st.markdown(f"🔗 [Ver firma en Google Drive]({url_firma})")
                    else:
                        st.info("✍️ No hay firma disponible")
                
                # Detalles de la activación mejorados
                with st.expander("📋 Ver detalles completos de la activación"):
                    # Crear un DataFrame con los detalles
                    detalles = {
                        'Campo': ['Activador', 'Canal', 'Ubicación', 'Fecha', 'Cumplió meta', 'Ventas (kg)', 'Ticket promedio', 'Incidencias'],
                        'Valor': [
                            row.get('Activador de Marca', 'N/A'),
                            row.get('Canal de Activación', 'N/A'),
                            row.get('Lugar / Dirección del punto', 'N/A'),
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
        
        # Seleccionar columnas para mostrar
        columnas_mostrar = [
            'Fecha de Activación',
            'Activador de Marca',
            'Canal de Activación',
            'Lugar / Dirección del punto',
            '¿Se cumplió la meta?',
            'Ventas_netas_limpias',
            'Ticket_limpo',
            'Incidencias_detectadas'
        ]
        
        columnas_existentes = [col for col in columnas_mostrar if col in df_filtrado.columns]
        
        if columnas_existentes:
            df_tabla = df_filtrado[columnas_existentes].copy()
            # Renombrar columnas para mejor visualización
            renombres = {
                'Fecha de Activación': '📅 Fecha',
                'Activador de Marca': '👤 Activador',
                'Canal de Activación': '🏪 Canal',
                'Lugar / Dirección del punto': '📍 Ubicación',
                '¿Se cumplió la meta?': '✅ Meta',
                'Ventas_netas_limpias': '💰 Ventas (kg)',
                'Ticket_limpo': '💳 Ticket ($)',
                'Incidencias_detectadas': '⚠️ Incidencias'
            }
            df_tabla = df_tabla.rename(columns={k: v for k, v in renombres.items() if k in df_tabla.columns})
            
            st.dataframe(
                df_tabla, 
                use_container_width=True, 
                height=400,
                column_config={
                    "💳 Ticket ($)": st.column_config.NumberColumn(format="$%.0f"),
                    "💰 Ventas (kg)": st.column_config.NumberColumn(format="%.0f kg")
                }
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
