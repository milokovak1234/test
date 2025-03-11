import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import sqlite3
import pandas as pd
from database.location_manager import LocationManager
from database.db_utils import get_db_connection, LocationDB, ProcessHistoryDB

# Page configuration
st.set_page_config(
    page_title="WMS Operations",
    page_icon="🏭",
    layout="wide"
)

st.title("Operaciones WMS")

# Sidebar for operation selection
st.sidebar.title("Menú de Operaciones")

# Define WMS operations
operations = {
    "Recepción": {
        "icon": "📦",
        "description": "Gestionar la entrada de mercancía, validación y asignación de ubicaciones",
        "sub_operations": [
            "Recepción de Órdenes de Compra",
            "Control de Calidad en Recepción",
            "Etiquetado y Registro",
            "Asignación de Ubicaciones"
        ]
    },
    "Almacenamiento": {
        "icon": "🏪",
        "description": "Administrar el almacenamiento y reubicación de productos",
        "sub_operations": [
            "Putaway",
            "Reubicación de Productos",
            "Optimización de Espacio",
            "Gestión de Zonas"
        ]
    },
    "Picking": {
        "icon": "🛒",
        "description": "Gestionar la preparación y recolección de pedidos",
        "sub_operations": [
            "Picking por Pedido",
            "Picking por Lote",
            "Wave Picking",
            "Pick to Light"
        ]
    },
    "Inventario": {
        "icon": "📊",
        "description": "Control y gestión del inventario",
        "sub_operations": [
            "Conteo Cíclico",
            "Ajustes de Inventario",
            "Reportes de Stock",
            "Gestión de Discrepancias"
        ]
    },
    "Despacho": {
        "icon": "🚚",
        "description": "Preparación y envío de pedidos",
        "sub_operations": [
            "Consolidación de Pedidos",
            "Empaque",
            "Verificación de Envíos",
            "Documentación de Despacho"
        ]
    },
    "Calidad": {
        "icon": "✅",
        "description": "Control de calidad y gestión de no conformidades",
        "sub_operations": [
            "Inspección de Calidad",
            "Gestión de Rechazos",
            "Cuarentena",
            "Trazabilidad"
        ]
    },
    "Reportes": {
        "icon": "📈",
        "description": "Informes y análisis de operaciones",
        "sub_operations": [
            "KPIs Operacionales",
            "Análisis de Productividad",
            "Reportes de Utilización",
            "Histórico de Movimientos"
        ]
    }
}

# Operation selection
selected_operation = st.sidebar.selectbox(
    "Seleccionar Operación",
    options=list(operations.keys()),
    format_func=lambda x: f"{operations[x]['icon']} {x}"
)

# Display operation details 
if selected_operation:
    operation = operations[selected_operation]
    
    # Main content area
    st.header(f"{operation['icon']} {selected_operation}")
    st.write(operation['description'])
    
    # Display sub-operations in columns
    st.subheader("Procesos Disponibles")
    cols = st.columns(2)
    
    # Store the selected sub-operation in session state if not already present
    if 'selected_sub_operation' not in st.session_state:
        st.session_state.selected_sub_operation = None
    
    # Display sub-operations as selectable buttons
    for i, sub_op in enumerate(operation['sub_operations']):
        with cols[i % 2]:
            if st.button(f"🔹 {sub_op}", key=f"sub_op_{selected_operation}_{i}"):
                st.session_state.selected_sub_operation = sub_op
    
    # Display selected sub-operation content
    if st.session_state.selected_sub_operation:
        st.write("---")
        st.subheader(f"Proceso: {st.session_state.selected_sub_operation}")
        
        # Add specific content for each sub-operation
        if st.session_state.selected_sub_operation == "Recepción de Órdenes de Compra":
            from pages._recepcion_ordenes import render_recepcion_ordenes
            render_recepcion_ordenes()
        elif st.session_state.selected_sub_operation == "Asignación de Ubicaciones":
            from pages._asignar_ubicaciones import render_asignar_ubicaciones
            render_asignar_ubicaciones()
        else:
            st.info(f"Implementación del proceso '{st.session_state.selected_sub_operation}' en desarrollo.")
        
        # Add a button to clear selection
        if st.button("Volver a la lista de procesos"):
            st.session_state.selected_sub_operation = None
            st.rerun()
    else:
        st.write("---")
        st.info("Seleccione un proceso específico para comenzar.")

# Footer
st.markdown("---")

# Process History Table
st.subheader("📋 Historial de Procesos")

# Get process history from database
process_history = ProcessHistoryDB.get_process_history()

if process_history:
    # Convert to DataFrame for better display
    history_data = [
        {
            "Operación": f"{ph['operation_type']}",
            "Subproceso": ph['sub_operation'],
            "Estado": ph['status'],
            "Fecha": ph['timestamp'],
            "Detalles": ph['details'] or "",
            "Usuario": ph['user_id'] or "Sistema"
        } for ph in process_history
    ]
    
    st.dataframe(
        pd.DataFrame(history_data),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No hay procesos registrados aún.")

# WMS Footer
st.markdown("<div style='text-align: center'>WMS Lite - Sistema de Gestión de Almacenes</div>", unsafe_allow_html=True)