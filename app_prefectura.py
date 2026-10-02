import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os

st.set_page_config(page_title="Reportes de Prefectura CETIS 79", layout="centered", page_icon="📋")

# Archivo central donde se guardarán todos los reportes del día
ARCHIVO_CENTRAL = "reportes_diarios.csv"

@st.cache_data
def cargar_datos():
    return pd.read_csv("base_maestros_cetis79.csv")

try:
    df_horarios = cargar_datos()
except FileNotFoundError:
    st.error("No se encontró el archivo base_maestros_cetis79.csv.")
    st.stop()

st.title("📋 Reportes de Incidencias - Prefectura")

dias_semana = {0: "LUNES", 1: "MARTES", 2: "MIERCOLES", 3: "JUEVES", 4: "VIERNES", 5: "SABADO", 6: "DOMINGO"}

# --- 0. IDENTIFICACIÓN DEL PREFECTO ---
st.markdown("### Datos del Prefecto")
nombre_prefecto = st.text_input("Nombre del prefecto en turno:", placeholder="Ej. Juan Pérez")

st.divider()

# --- 1. CAPTURAR INCIDENCIA ---
st.header("1. Buscar y Capturar Incidencia")

fecha_seleccionada = st.date_input("Fecha de la incidencia")
dia_texto = dias_semana[fecha_seleccionada.weekday()]

if dia_texto in ["SABADO", "DOMINGO"]:
    st.warning("Seleccionaste un fin de semana. Elige un día de Lunes a Viernes.")
else:
    df_dia = df_horarios[df_horarios['DIA'] == dia_texto].copy()
    
    st.markdown("#### Filtros de Búsqueda")
    col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
    
    with col_filtro1:
        lista_docentes = ["Todos"] + sorted(df_dia['DOCENTE'].unique())
        filtro_docente = st.selectbox("Docente", lista_docentes)
        
    with col_filtro2:
        lista_grupos = ["Todos"] + sorted(df_dia['GRADO_GRUPO'].unique())
        filtro_grupo = st.selectbox("Grupo", lista_grupos)
        
    with col_filtro3:
        lista_materias = ["Todas"] + sorted(df_dia['MATERIA'].unique())
        filtro_materia = st.selectbox("Materia", lista_materias)

    if filtro_docente != "Todos":
        df_dia = df_dia[df_dia['DOCENTE'] == filtro_docente]
    if filtro_grupo != "Todos":
        df_dia = df_dia[df_dia['GRADO_GRUPO'] == filtro_grupo]
    if filtro_materia != "Todas":
        df_dia = df_dia[df_dia['MATERIA'] == filtro_materia]

    st.markdown("#### Seleccionar Clase Afectada")
    if df_dia.empty:
        st.warning("No se encontraron clases con esos filtros en este día.")
    else:
        opciones_clases = []
        for idx, row in df_dia.iterrows():
            opciones_clases.append(f"{row['MODULO']} | Grupo: {row['GRADO_GRUPO']} | {row['DOCENTE']} | {row['MATERIA']}")
            
        clase_seleccionada = st.selectbox("Elige la clase donde ocurrió la incidencia:", opciones_clases)
        
        indice_elegido = opciones_clases.index(clase_seleccionada)
        datos_clase = df_dia.iloc[indice_elegido]
        
        col_inc1, col_inc2 = st.columns(2)
        with col_inc1:
            tipo_incidencia = st.radio("Tipo:", ["FALTA", "RETARDO"])
        with col_inc2:
            hora_retardo = ""
            if tipo_incidencia == "RETARDO":
                hora_retardo = st.text_input("Hora exacta del retardo (ej. 18:10)")
                
        if st.button("➕ Agregar al Reporte Global", type="primary"):
            if not nombre_prefecto:
                st.error("⚠️️ Debes ingresar tu nombre de prefecto en la parte superior antes de registrar.")
            else:
                grado = datos_clase['GRADO_GRUPO'].split('°')[0] if '°' in datos_clase['GRADO_GRUPO'] else ""
                grupo = datos_clase['GRADO_GRUPO'].split('°')[1].strip() if '°' in datos_clase['GRADO_GRUPO'] else datos_clase['GRADO_GRUPO']
                
                nuevo_reporte = {
                    "FECHA": fecha_seleccionada.strftime("%d/%m/%Y"),
                    "DIA": dia_texto,
                    "DOCENTE": datos_clase['DOCENTE'],
                    "MODULO": datos_clase['MODULO'],
                    "FALTA": "FALTA" if tipo_incidencia == "FALTA" else "",
                    "RETARDO": hora_retardo if tipo_incidencia == "RETARDO" else "",
                    "GRADO": grado,
                    "GRUPO": grupo,
                    "PREFECTO_QUE_REPORTA": nombre_prefecto
                }
                
                # Guardar en el archivo centralizado
                df_nuevo = pd.DataFrame([nuevo_reporte])
                if os.path.exists(ARCHIVO_CENTRAL):
                    df_existente = pd.read_csv(ARCHIVO_CENTRAL)
                    df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
                else:
                    df_final = df_nuevo
                    
                df_final.to_csv(ARCHIVO_CENTRAL, index=False)
                st.success(f"Registrado correctamente en la base central por {nombre_prefecto}.")

st.divider()

# --- 2. VISTA PREVIA Y EXPORTACIÓN GLOBAL ---
st.header("2. Reporte Final del Día")

if os.path.exists(ARCHIVO_CENTRAL):
    df_reporte = pd.read_csv(ARCHIVO_CENTRAL)
    
    st.dataframe(df_reporte, use_container_width=True)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_reporte.to_excel(writer, index=False, sheet_name='Reporte_Diario')
        
    st.download_button(
        label="📥 Descargar Excel con TODOS los reportes",
        data=buffer.getvalue(),
        file_name=f"Reporte_Global_Prefectura_{datetime.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    if st.button("🗑️ Borrar base de datos (Usar al final del día)"):
        os.remove(ARCHIVO_CENTRAL)
        st.rerun()
else:
    st.info("Aún no hay incidencias capturadas el día de hoy.")