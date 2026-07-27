import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import re

# Configuración de la página
st.set_page_config(page_title="BTL Command Center", layout="wide")

# Título principal
st.title("🎯 Centro de Control - Activaciones Pollo Fiesta")
st.markdown("---")

# 🔴 URL de tu Google Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/1fFcgK4ikmaEDXXesAc7wljONAyYx0b-0DAhjGa4vZqg/export?format=csv"

# Funciones de limpieza
def limpiar_ventas(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    numeros = re.findall(r'[\d,]+', str(valor))
    if numeros:
        return float(numeros[0].replace(',', ''))
    return None

def limpiar_ticket(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    limpio = re.sub(r'[^\d,]', '', str(valor))
    if limpio:
        return float(limpio.replace(',', ''))
    return None

def extraer_nombre_lugar(direccion):
    if pd.isna(direccion):
        return "Ubicación desconocida"
    lugares = ['Jumbo', 'Metro', 'PDV', 'Merkacol', 'Supertiendas', 'Plaza', 'Camacho', 'Avicola']
    for lugar in lugares:
        if lugar.lower() in str(direccion).lower():
            return lugar
    return str(direccion)[:30]

def convertir_fecha_segura(fecha_str):
    if pd.isna(fecha_str):
        return pd.NaT
    try:
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
            try:
                return pd.to_datetime(fecha_str, format=fmt)
            except:
                continue
        return pd.to_datetime(fecha_str, errors='coerce')
    except:
        return pd.NaT

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
        
        # Extraer nombre del lugar
        if 'Lugar / Dirección del punto' in df.columns:
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
            'lluvia': ['lluvia', 'lluvioso', 'lloviendo'],
            'clima adverso': ['clima', 'frío', 'calor', 'temperatura'],
            'competencia': ['competencia', 'competidor'],
            'poca afluencia': ['poca afluencia', 'poco público', 'baja afluencia'],
            'problemas logísticos': ['inventario', 'pedido', 'llegó', 'retraso', 'demora'],
            'problemas técnicos': ['nevera', 'falla', 'técnica']
        }
        
        df['Incidencias_detectadas'] = ''
        for idx, row in df.iterrows():
            texto = str(row['Texto_completo']).lower()
            incidencias = []
            for categoria, palabras in incidencias_keywords.items():
                for palabra in palabras:
                    if palabra in texto:
                        incidencias.append(categoria)
                        break
            df.at[idx, 'Incidencias_detectadas'] = ', '.join(set(incidencias)) if incidencias else 'Sin incidencias'
        
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
    st.sidebar.title("🔍 Filtros")
    
    # Filtro de activador
    if 'Activador de Marca' in df.columns:
        activadores = ['Todos'] + list(df['Activador de Marca'].unique())
        activador_seleccionado = st.sidebar.selectbox("Selecciona Activador", activadores)
    else:
        activador_seleccionado = 'Todos'
    
    # Filtro de canal
    if 'Canal de Activación' in df.columns:
        canales = ['Todos'] + list(df['Canal de Activación'].unique())
        canal_seleccionado = st.sidebar.selectbox("Selecciona Canal", canales)
    else:
        canal_seleccionado = 'Todos'
    
    # Filtro de fecha
    if 'Fecha' in df.columns and len(df) > 0:
        fecha_min = df['Fecha'].min().date()
        fecha_max = df['Fecha'].max().date()
        fecha_inicio = st.sidebar.date_input("Fecha desde", fecha_min, min_value=fecha_min, max_value=fecha_max)
        fecha_fin = st.sidebar.date_input("Fecha hasta", fecha_max, min_value=fecha_min, max_value=fecha_max)
    else:
        fecha_inicio = None
        fecha_fin = None
    
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
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"📊 Mostrando {len(df_filtrado)} de {len(df)} activaciones")
    
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
            st.metric("💰 Ventas Totales (kg)", f"{total_ventas:,.0f}" if pd.notna(total_ventas) else "N/A")
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
                text='Número de Activaciones'
            )
            fig1.update_traces(textposition='outside')
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Datos no disponibles")
    
    with col2:
        st.subheader("🏪 Activaciones por Canal")
        if 'Canal de Activación' in df_filtrado.columns and len(df_filtrado) > 0:
            conteo_canal = df_filtrado['Canal de Activación'].value_counts().reset_index()
            conteo_canal.columns = ['Canal', 'Número de Activaciones']
            
            fig2 = px.pie(
                conteo_canal,
                names='Canal',
                values='Número de Activaciones',
                title="Distribución por canal"
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Datos no disponibles")
    
    # ==================== MAPA ====================
    if len(df_filtrado) > 0:
        st.markdown("---")
        st.subheader("📍 Mapa de Activaciones")
        
        if 'Lugar / Dirección del punto' in df_filtrado.columns:
            ubicaciones_conocidas = {
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
                'Altos del Country': {'lat': 4.7100, 'lon': -74.0300}
            }
            
            df_filtrado['Latitud'] = 4.7110
            df_filtrado['Longitud'] = -74.0721
            
            for ubicacion, coords in ubicaciones_conocidas.items():
                mascara = df_filtrado['Lugar / Dirección del punto'].str.contains(ubicacion, case=False, na=False)
                df_filtrado.loc[mascara, 'Latitud'] = coords['lat']
                df_filtrado.loc[mascara, 'Longitud'] = coords['lon']
            
            fig_mapa = px.scatter_mapbox(
                df_filtrado,
                lat="Latitud",
                lon="Longitud",
                hover_name="Activador de Marca" if 'Activador de Marca' in df_filtrado.columns else None,
                hover_data={
                    'Lugar / Dirección del punto': True,
                    'Canal de Activación': True,
                    '¿Se cumplió la meta?': True
                } if 'Canal de Activación' in df_filtrado.columns else None,
                color="Activador de Marca" if 'Activador de Marca' in df_filtrado.columns else None,
                size_max=15,
                zoom=9,
                title="Ubicación de activaciones en Bogotá y alrededores"
            )
            
            fig_mapa.update_layout(
                mapbox_style="open-street-map",
                height=500
            )
            
            st.plotly_chart(fig_mapa, use_container_width=True)
        else:
            st.info("No se encontró la columna de ubicación para el mapa")
    
    # ==================== GRÁFICOS ADICIONALES ====================
    if len(df_filtrado) > 0:
        st.markdown("---")
        st.subheader("📈 Análisis de Desempeño")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'Fecha' in df_filtrado.columns and 'Ventas_netas_limpias' in df_filtrado.columns:
                ventas_por_dia = df_filtrado.groupby(df_filtrado['Fecha'].dt.date)['Ventas_netas_limpias'].sum().reset_index()
                ventas_por_dia.columns = ['Fecha', 'Ventas (kg)']
                
                if len(ventas_por_dia) > 0:
                    fig_ventas = px.line(
                        ventas_por_dia,
                        x='Fecha',
                        y='Ventas (kg)',
                        title="Ventas por día",
                        markers=True
                    )
                    st.plotly_chart(fig_ventas, use_container_width=True)
                else:
                    st.info("No hay datos de ventas por día")
            else:
                st.info("Datos de ventas por día no disponibles")
        
        with col2:
            if 'Ticket_limpo' in df_filtrado.columns:
                tickets = df_filtrado['Ticket_limpo'].dropna()
                tickets = tickets[tickets > 0]
                
                if len(tickets) > 0:
                    fig_ticket = px.box(
                        y=tickets,
                        title="Distribución del Ticket Promedio",
                        labels={'y': 'Ticket Promedio ($)'}
                    )
                    st.plotly_chart(fig_ticket, use_container_width=True)
                else:
                    st.info("No hay datos de ticket promedio disponibles")
            else:
                st.info("Datos de ticket promedio no disponibles")
    
    # ==================== CUMPLIMIENTO ====================
    if len(df_filtrado) > 0:
        st.markdown("---")
        st.subheader("📊 Análisis de Cumplimiento de Meta")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if '¿Se cumplió la meta?' in df_filtrado.columns:
                fig3 = px.pie(
                    df_filtrado,
                    names='¿Se cumplió la meta?',
                    title="Cumplimiento de Meta",
                    color_discrete_map={'Si': '#2ecc71', 'No': '#e74c3c', 'Parcialmente': '#f39c12'}
                )
                st.plotly_chart(fig3, use_container_width=True)
        
        with col2:
            if 'Canal de Activación' in df_filtrado.columns and '¿Se cumplió la meta?' in df_filtrado.columns:
                cumplimiento_canal = df_filtrado.groupby('Canal de Activación')['¿Se cumplió la meta?'].apply(
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
                        title="Distribución de Incidencias"
                    )
                    st.plotly_chart(fig_incidencias, use_container_width=True)
                
                with col2:
                    st.subheader("📋 Activaciones con Incidencias")
                    
                    # ===== CORRECCIÓN: Solo usar columnas que existen =====
                    columnas_disponibles = ['Fecha de Activación', 'Activador de Marca', 'Canal de Activación', 
                                           'Lugar / Dirección del punto', '¿Se cumplió la meta?', 'Incidencias_detectadas']
                    columnas_existentes = [col for col in columnas_disponibles if col in df_filtrado.columns]
                    
                    df_incidencias_detalle = df_filtrado[df_filtrado['Incidencias_detectadas'] != 'Sin incidencias'][columnas_existentes].copy()
                    
                    if len(df_incidencias_detalle) > 20:
                        st.warning(f"Mostrando 20 de {len(df_incidencias_detalle)} activaciones con incidencias")
                        df_incidencias_detalle = df_incidencias_detalle.head(20)
                    
                    st.dataframe(df_incidencias_detalle, use_container_width=True)
                    
                    if '¿Se cumplió la meta?' in df_incidencias_detalle.columns:
                        blindadas = df_incidencias_detalle[df_incidencias_detalle['¿Se cumplió la meta?'] == 'Si']
                        if len(blindadas) > 0:
                            st.success(f"🛡️ {len(blindadas)} activaciones tuvieron incidencias pero cumplieron la meta - ¡Activadores blindados!")
            else:
                st.info("✅ No se detectaron incidencias en las activaciones")
    
    # ==================== VISOR DE FOTOS ====================
       # ==================== VISOR DE FOTOS ====================
    if len(df_filtrado) > 0:
        st.markdown("---")
        st.subheader("📸 Visor de Fotos - Evidencia en Campo")
        
        if 'Fecha de Activación' in df_filtrado.columns and 'Activador de Marca' in df_filtrado.columns:
            opciones = []
            for idx, row in df_filtrado.iterrows():
                fecha = row.get('Fecha de Activación', 'Sin fecha')
                activador = row.get('Activador de Marca', 'Sin activador')
                lugar = row.get('Lugar / Dirección del punto', 'Sin lugar')
                opciones.append(f"{fecha} - {activador} - {lugar}")
            
            if opciones:
                seleccion = st.selectbox("Selecciona una activación para ver las fotos:", opciones)
                
                if seleccion:
                    idx = opciones.index(seleccion)
                    row = df_filtrado.iloc[idx]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**📸 Foto del Lineal o Vitrina**")
                        url_foto = row.get('Foto del lineal o vitrina (obligatoria)', '')
                        if pd.notna(url_foto) and url_foto:
                            # Intentar extraer el ID de Google Drive
                            import re
                            # Buscar el ID en cualquier formato de link de Google Drive
                            match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', str(url_foto))
                            if match:
                                file_id = match.group(1)
                                # Usar el formato embed que funciona mejor
                                embed_url = f"https://drive.google.com/thumbnail?export=view&id={file_id}"
                                st.image(embed_url, use_container_width=True)
                            elif 'open?id=' in str(url_foto):
                                file_id = str(url_foto).split('open?id=')[1].split('&')[0]
                                embed_url = f"https://drive.google.com/thumbnail?export=view&id={file_id}"
                                st.image(embed_url, use_container_width=True)
                            elif 'uc?export=view' in str(url_foto):
                                st.image(url_foto, use_container_width=True)
                            else:
                                # Intentar mostrar como HTML
                                st.markdown(f'<a href="{url_foto}" target="_blank">Ver imagen en Google Drive</a>', unsafe_allow_html=True)
                        else:
                            st.info("No hay foto disponible")
                    
                    with col2:
                        st.markdown("**✍️ Firma del Administrador**")
                        url_firma = row.get('Firma de quien califica', '')
                        if pd.notna(url_firma) and url_firma:
                            import re
                            match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', str(url_firma))
                            if match:
                                file_id = match.group(1)
                                embed_url = f"https://drive.google.com/thumbnail?export=view&id={file_id}"
                                st.image(embed_url, use_container_width=True)
                            elif 'open?id=' in str(url_firma):
                                file_id = str(url_firma).split('open?id=')[1].split('&')[0]
                                embed_url = f"https://drive.google.com/thumbnail?export=view&id={file_id}"
                                st.image(embed_url, use_container_width=True)
                            elif 'uc?export=view' in str(url_firma):
                                st.image(url_firma, use_container_width=True)
                            else:
                                st.markdown(f'<a href="{url_firma}" target="_blank">Ver imagen en Google Drive</a>', unsafe_allow_html=True)
                        else:
                            st.info("No hay firma disponible")
                    
                    with st.expander("📋 Ver detalles de la activación"):
                        detalles = {
                            'Activador': row.get('Activador de Marca', 'N/A'),
                            'Canal': row.get('Canal de Activación', 'N/A'),
                            'Ubicación': row.get('Lugar / Dirección del punto', 'N/A'),
                            'Cumplió meta': row.get('¿Se cumplió la meta?', 'N/A'),
                            'Ventas (kg)': row.get('Ventas_netas_limpias', 'N/A'),
                            'Incidencias': row.get('Incidencias_detectadas', 'Sin incidencias')
                        }
                        st.json(detalles)
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
            'Lugar / Dirección del punto',
            '¿Se cumplió la meta?',
            'Ventas_netas_limpias',
            'Incidencias_detectadas'
        ]
        
        columnas_existentes = [col for col in columnas_mostrar if col in df_filtrado.columns]
        
        if columnas_existentes:
            st.dataframe(df_filtrado[columnas_existentes], use_container_width=True, height=400)
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
