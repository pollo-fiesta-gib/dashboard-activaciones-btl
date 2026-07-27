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

def get_semaforo(valor):
    """Retorna emoji y color según cumplimiento"""
    if valor == 'Si':
        return "🟢", "#d4edda", "#155724"
    elif valor == 'Parcialmente':
        return "🟡", "#fff3cd", "#856404"
    elif valor == 'No':
        return "🔴", "#f8d7da", "#721c24"
    else:
        return "⚪", "#f8f9fa", "#6c757d"

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
        cumplimiento_canal = df_filtrado.groupby('Canal de Activación')['¿Se cumplió la meta?'].apply(
            lambda x: (x == 'Si').sum() / len(x) * 100
        ).reset_index()
        cumplimiento_canal.columns = ['Canal', 'Cumplimiento %']
        cumplimiento_canal = cumplimiento_canal.sort_values('Cumplimiento %', ascending=False)
        
        def get_semaforo_canal(valor):
            if valor >= 80:
                return "🟢", "Verde"
            elif valor >= 50:
                return "🟡", "Amarillo"
            else:
                return "🔴", "Rojo"
        
        cumplimiento_canal['Semáforo'], cumplimiento_canal['Estado'] = zip(*cumplimiento_canal['Cumplimiento %'].apply(get_semaforo_canal))
        
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
    
    # ==================== TABLA DETALLADA CON SEMÁFORO Y FILTRO ====================
    st.markdown("## 📋 Detalle de Activaciones")
    
    # ===== FILTRO DE LA TABLA =====
    col_filtro1, col_filtro2, col_filtro3 = st.columns([2, 2, 1])
    
    with col_filtro1:
        filtro_meta = st.selectbox(
            "🔍 Filtrar por cumplimiento:",
            ["Todos", "✅ Cumplieron (Si)", "🟡 Parciales", "❌ No cumplieron"]
        )
    
    with col_filtro2:
        # Filtro adicional por activador dentro de la tabla
        if 'Activador de Marca' in df_filtrado.columns:
            activadores_tabla = ['Todos'] + list(df_filtrado['Activador de Marca'].unique())
            filtro_activador_tabla = st.selectbox("👤 Filtrar por activador:", activadores_tabla)
        else:
            filtro_activador_tabla = 'Todos'
    
    with col_filtro3:
        # Mostrar contador
        st.metric("📊 Registros", len(df_filtrado))
    
    # Aplicar filtros a la tabla
    df_tabla = df_filtrado.copy()
    
    if filtro_meta != "Todos":
        if filtro_meta == "✅ Cumplieron (Si)":
            df_tabla = df_tabla[df_tabla['¿Se cumplió la meta?'] == 'Si']
        elif filtro_meta == "🟡 Parciales":
            df_tabla = df_tabla[df_tabla['¿Se cumplió la meta?'] == 'Parcialmente']
        elif filtro_meta == "❌ No cumplieron":
            df_tabla = df_tabla[df_tabla['¿Se cumplió la meta?'] == 'No']
    
    if filtro_activador_tabla != 'Todos' and 'Activador de Marca' in df_tabla.columns:
        df_tabla = df_tabla[df_tabla['Activador de Marca'] == filtro_activador_tabla]
    
    # ===== CONSTRUIR LA TABLA CON SEMÁFORO =====
    if len(df_tabla) > 0:
        # Seleccionar columnas
        columnas_mostrar = [
            'Fecha de Activación',
            'Hora de Activación según cronograma',
            'Activador de Marca',
            'Canal de Activación',
            'Lugar / Dirección del punto (ejm. PDV Cabaña, Asadero Sede 1 Suba, Jumbo 170, etc)',
            '¿Se cumplió la meta?',
            'Meta de Ventas en kilos y/o unidades (ej: 150 kilos de pechuga, 30 combos, bandejas por fecha, etc.)',
            'Ventas netas aproximadas (en kilos, poner únicamente cifra)',
            'Observaciones del estado inicial',
            '¿Cuál fue la razón principal del resultado?',
            '¿Qué producto gustó más?',
            'Percepción de precio por los clientes (1 es malo 5 es óptimo)',
            'Incidencias_detectadas'
        ]
        
        # Filtrar solo columnas que existen
        columnas_existentes = [col for col in columnas_mostrar if col in df_tabla.columns]
        
        if columnas_existentes:
            df_tabla_display = df_tabla[columnas_existentes].copy()
            
            # Renombrar columnas para mejor visualización
            renombres = {
                'Fecha de Activación': '📅 Fecha',
                'Hora de Activación según cronograma': '🕐 Hora',
                'Activador de Marca': '👤 Activador',
                'Canal de Activación': '🏪 Canal',
                'Lugar / Dirección del punto (ejm. PDV Cabaña, Asadero Sede 1 Suba, Jumbo 170, etc)': '📍 Lugar',
                '¿Se cumplió la meta?': '✅ Meta',
                'Meta de Ventas en kilos y/o unidades (ej: 150 kilos de pechuga, 30 combos, bandejas por fecha, etc.)': '📊 Meta',
                'Ventas netas aproximadas (en kilos, poner únicamente cifra)': '💰 Ventas (kg)',
                'Observaciones del estado inicial': '📝 Estado inicial',
                '¿Cuál fue la razón principal del resultado?': '📌 Razón del resultado',
                '¿Qué producto gustó más?': '🏆 Producto destacado',
                'Percepción de precio por los clientes (1 es malo 5 es óptimo)': '💲 Percepción precio',
                'Incidencias_detectadas': '⚠️ Incidencias'
            }
            df_tabla_display = df_tabla_display.rename(columns={k: v for k, v in renombres.items() if k in df_tabla_display.columns})
            
            # ===== APLICAR SEMÁFORO A LA COLUMNA META =====
            def aplicar_semaforo_fila(row):
                meta = row.get('✅ Meta', '')
                if meta == 'Si':
                    return ['background-color: #d4edda; color: #155724; font-weight: bold;'] * len(row)
                elif meta == 'Parcialmente':
                    return ['background-color: #fff3cd; color: #856404; font-weight: bold;'] * len(row)
                elif meta == 'No':
                    return ['background-color: #f8d7da; color: #721c24; font-weight: bold;'] * len(row)
                else:
                    return [''] * len(row)
            
            # Aplicar estilo a la columna Meta
            styled_df = df_tabla_display.style.apply(aplicar_semaforo_fila, axis=1)
            
            # Mostrar tabla con semáforo
            st.dataframe(
                styled_df,
                use_container_width=True,
                height=400,
                column_config={
                    "✅ Meta": st.column_config.TextColumn("✅ Meta", width="small"),
                    "🕐 Hora": st.column_config.TextColumn("🕐 Hora", width="small"),
                    "📍 Lugar": st.column_config.TextColumn("📍 Lugar", width="medium"),
                    "💲 Percepción precio": st.column_config.NumberColumn("💲 Percepción precio", min_value=1, max_value=5, format="%d ⭐"),
                }
            )
            
            # ===== CONTADORES DE LA TABLA =====
            st.markdown("---")
            col_c1, col_c2, col_c3 = st.columns(3)
            
            with col_c1:
                total_si = len(df_tabla[df_tabla['¿Se cumplió la meta?'] == 'Si']) if '¿Se cumplió la meta?' in df_tabla.columns else 0
                st.metric("✅ Cumplieron", total_si)
            
            with col_c2:
                total_parcial = len(df_tabla[df_tabla['¿Se cumplió la meta?'] == 'Parcialmente']) if '¿Se cumplió la meta?' in df_tabla.columns else 0
                st.metric("🟡 Parciales", total_parcial)
            
            with col_c3:
                total_no = len(df_tabla[df_tabla['¿Se cumplió la meta?'] == 'No']) if '¿Se cumplió la meta?' in df_tabla.columns else 0
                st.metric("🔴 No cumplieron", total_no)
            
            # ===== MOSTRAR ALERTA SI HAY MUCHOS "NO" =====
            if total_no > 0:
                porcentaje_no = (total_no / len(df_tabla)) * 100
                if porcentaje_no > 30:
                    st.error(f"🔴 **ALERTA:** {total_no} activaciones ({porcentaje_no:.0f}%) NO cumplieron la meta. Revisar estrategia.")
                elif porcentaje_no > 15:
                    st.warning(f"🟡 **ATENCIÓN:** {total_no} activaciones ({porcentaje_no:.0f}%) NO cumplieron la meta. Requiere seguimiento.")
        else:
            st.info("No hay columnas disponibles para mostrar la tabla")
    else:
        st.info("No hay activaciones que coincidan con los filtros seleccionados")
    
    # ==================== PIE DE PÁGINA ====================
    st.markdown("---")
    st.caption(f"🔄 Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M')} | {len(df_filtrado)} activaciones mostradas")

else:
    st.error("❌ No se pudieron cargar los datos. Verifica la URL de Google Sheets.")
    st.info("Asegúrate de que el archivo esté compartido como 'Cualquier persona con el enlace puede ver'")
