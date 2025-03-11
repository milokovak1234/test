import streamlit as st
import pandas as pd
import sqlite3
from dotenv import load_dotenv
import os
from database.db_utils import init_database, ProductDB, InventoryDB, LocationDB, OrderDB, ProcessHistoryDB

# Load environment variables
load_dotenv()
# la url es http://192.168.100.8:8501/ actualmente, hay que cambiarlo(http://[machine-ip]:8501) para que funcione

# Initialize database
init_database()

# Configure the page
st.set_page_config(
    page_title="WMS Lite",
    page_icon="🏭",
    layout="wide"
)

# Main application layout
st.title('WMS Lite 📦')

# Sidebar for navigation
st.sidebar.title('Navegación')
option = st.sidebar.selectbox(
    'Seleccionar página',
    ['Panel Principal', 'Gestión de Productos', 'Gestión de Zonas']
)

# Main content area
if option == 'Panel Principal':
    st.header('Panel Principal')
    st.write('Bienvenido a WMS Lite - Tu Solución de Gestión de Almacenes')
    
    # Dashboard metrics in a 2x2 grid
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    # First row
    with col1:
        products = len(ProductDB.get_all_products())
        st.metric(label="Total de Productos", value=products)

    with col2:
        locations = len(LocationDB.get_all_locations())
        st.metric(label="Total de Ubicaciones", value=locations)

    # Second row
    with col3:
        categories = len(ProductDB.get_all_categories())
        st.metric(label="Categorías de Productos", value=categories)

    with col4:
        inventory = InventoryDB.get_inventory_levels()
        low_stock = sum(1 for item in inventory if item['quantity'] <= item['min_quantity'])
        st.metric(label="Productos con Bajo Stock", value=low_stock)

    # Additional warehouse insights
    st.subheader("Resumen del Almacén")
    
    # Orders summary
    orders = OrderDB.get_all_orders()
    pending_orders = sum(1 for order in orders if order['status'] == 'pending')
    
    # Display orders information
    st.info(f"📦 Órdenes Pendientes: {pending_orders}")

    # Stock alerts
    if low_stock > 0:
        st.warning(f"⚠️ Hay {low_stock} productos con stock bajo que requieren atención")
    else:
        st.success("✅ Todos los productos tienen niveles de stock adecuados")

    # Recent activity
    st.subheader("Actividad Reciente")
    recent_history = ProcessHistoryDB.get_process_history(limit=5)
    
    if recent_history:
        for entry in recent_history:
            st.text(f"🔸 {entry['operation_type']} - {entry['sub_operation']} ({entry['status']})")
    else:
        st.write("No hay actividad reciente registrada")

elif option == 'Gestión de Productos':
    st.header('Gestión de Productos')
    # Keep all existing ABM PRODUCTOS code here
    # Category Management
    with st.expander("Gestión de Categorías"):
        # Add new category
        new_category = st.text_input("Nueva Categoría")
        if st.button("Agregar Categoría"):
            if new_category:
                try:
                    ProductDB.add_category(new_category)
                    st.success(f"¡Categoría {new_category} agregada exitosamente!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Esta categoría ya existe")
        
        # Display and manage existing categories
        categories = ProductDB.get_all_categories()
        if categories:
            st.subheader("Categorías Existentes")
            for category in categories:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(category['name'])
                with col2:
                    if st.button("🗑️", key=f"delete_category_{category['category_id']}"):
                        if ProductDB.delete_category(category['category_id']):
                            st.success("Categoría eliminada exitosamente")
                            st.rerun()
                        else:
                            st.error("No se puede eliminar la categoría porque tiene productos asociados")
    
    # Product Management
    with st.expander("Agregar Nuevo Producto"):
        categories = ProductDB.get_all_categories()
        if not categories:
            st.warning("Debe crear al menos una categoría antes de agregar productos")
        else:
            sku = st.text_input("SKU")
            code = st.text_input("Código")
            name = st.text_input("Nombre del Producto")
            description = st.text_area("Descripción")
            category_id = st.selectbox(
                "Categoría",
                options=[c['category_id'] for c in categories],
                format_func=lambda x: [c['name'] for c in categories if c['category_id'] == x][0]
            )
            stock = st.number_input("Stock Actual", min_value=0)
            min_stock = st.number_input("Stock Mínimo", min_value=0)
            max_stock = st.number_input("Stock Máximo", min_value=0)
            
            if st.button("Agregar Producto"):
                if max_stock < min_stock:
                    st.error("El stock máximo no puede ser menor que el stock mínimo")
                else:
                    product_id, is_duplicate = ProductDB.add_product(sku, code, name, description, category_id, min_stock, max_stock, stock)
                    if is_duplicate:
                        st.warning(f"¡Atención! Ya existe un producto con el SKU {sku}. Este producto se ha marcado como duplicado.")
                    st.success("¡Producto agregado exitosamente!")
                    st.rerun()
    
    # Search and Filter Section
    st.subheader("Buscar y Filtrar Productos")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Category filter
        categories = ProductDB.get_all_categories()
        category_options = ["Todas las Categorías"] + [cat["name"] for cat in categories]
        selected_category = st.selectbox("Filtrar por Categoría", options=category_options)
    
    with col2:
        # Search bar
        search_query = st.text_input("Buscar Productos", placeholder="Ingrese nombre, SKU o código del producto")
    
    # Filter and display products
    products = ProductDB.get_all_products()
    if products:
        # Convert to DataFrame for easier filtering
        df = pd.DataFrame(products)
        df.columns = ['ID', 'SKU', 'Código', 'Nombre', 'Descripción', 'Stock Mínimo', 'Stock Máximo', 'Stock', 'Categoría ID', 'Categoría']
        
        # Apply category filter
        if selected_category != "Todas las Categorías":
            df = df[df["Categoría"] == selected_category]
        
        # Apply search filter
        if search_query:
            search_query = search_query.lower()
            df = df[df.apply(lambda row: 
                search_query in str(row["Nombre"]).lower() or 
                search_query in str(row["SKU"]).lower() or 
                search_query in str(row["Código"]).lower(), axis=1
            )]
        
        # If no results after filtering
        if df.empty:
            st.info("No se encontraron productos que coincidan con los criterios de búsqueda")
            st.stop()
        
        # Continue with existing products display logic using filtered DataFrame
        products = df.to_dict("records")
        df = pd.DataFrame(products)
        df.columns = ['ID', 'SKU', 'Código', 'Nombre', 'Descripción', 'Stock Mínimo', 'Stock Máximo', 'Stock', 'Categoría ID', 'Categoría']
        
        # Add edit and delete buttons for each product
        for index, row in df.iterrows():
            with st.expander(f"{row['Nombre']} (SKU: {row['SKU']})"):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**Código:** {row['Código']}")
                    st.write(f"**Descripción:** {row['Descripción']}")
                    st.write(f"**Categoría:** {row['Categoría']}")
                    st.write(f"**Stock Mínimo:** {row['Stock Mínimo']}")
                    st.write(f"**Stock Máximo:** {row['Stock Máximo']}")
                with col2:
                    if st.button("🗑️ Eliminar", key=f"delete_product_{row['ID']}"):
                        # Add delete functionality here
                        st.warning("¿Está seguro de que desea eliminar este producto?")
                        if st.button("Confirmar Eliminación", key=f"confirm_delete_{row['ID']}"):
                            # Implement delete logic
                            st.success("Producto eliminado exitosamente")
                            st.rerun()
                with col3:
                    if st.button("✏️ Editar", key=f"edit_product_{row['ID']}"):
                        st.session_state['editing_product'] = row['ID']
                
                # Edit form
                if 'editing_product' in st.session_state and st.session_state['editing_product'] == row['ID']:
                    with st.form(key=f"edit_product_form_{row['ID']}"):
                        new_sku = st.text_input("SKU", value=row['SKU'])
                        new_code = st.text_input("Código", value=row['Código'])
                        new_name = st.text_input("Nombre", value=row['Nombre'])
                        new_description = st.text_area("Descripción", value=row['Descripción'])
                        new_min_stock = st.number_input("Stock Mínimo", value=row['Stock Mínimo'])
                        new_max_stock = st.number_input("Stock Máximo", value=row['Stock Máximo'])
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Guardar"):
                                # Implement update logic
                                st.session_state.pop('editing_product')
                                st.success("Producto actualizado exitosamente")
                                st.rerun()
                        with col2:
                            if st.form_submit_button("Cancelar"):
                                st.session_state.pop('editing_product')
                                st.rerun()
        
        # Display the table with proper headers
        st.dataframe(df)
    else:
        st.info("No se encontraron productos")

elif option == 'Gestión de Zonas':
    st.header('Gestión de Zonas')
    # Keep all existing ABM ZONAS code here
    # Zone Type Management
    with st.expander("Crear Nueva Zona"):
        zone_name = st.text_input("Nombre de la Zona", key="zone_creation_name_input")
        zone_type = st.selectbox("Tipo de Zona", [
            "Almacenamiento",
            "Cross-Docking",
            "Picking",
            "Packing",
            "Recepción",
            "Despacho",
            "Control de Calidad",
            "Devoluciones",
            "Materiales Peligrosos",
            "Almacenamiento en Frío",
            "Cuarentena",
            "Consolidación",
            "Valor Agregado"
        ])
        zone_description = st.text_area("Descripción de la Zona")
        
        # Add configuration for initial locations
        st.subheader("Configuración Inicial de Ubicaciones")
        col1, col2 = st.columns(2)
        with col1:
            num_aisles = st.number_input("Número de Pasillos", min_value=1, value=2)
            num_shelves = st.number_input("Estantes por Pasillo", min_value=1, value=2)
        with col2:
            num_positions = st.number_input("Posiciones por Estante", min_value=1, value=4)
        
        if st.button("Crear Zona"):
            try:
                # Create initial location to establish the zone
                LocationDB.add_location(zone_name, "1", "1", "1")
                
                # Create additional locations based on configuration
                locations_added = 0
                for aisle in range(1, num_aisles + 1):
                    for shelf in range(1, num_shelves + 1):
                        for position in range(1, num_positions + 1):
                            try:
                                LocationDB.add_location(zone_name, str(aisle), str(shelf), str(position))
                                locations_added += 1
                            except sqlite3.IntegrityError:
                                continue
                
                st.success(f"¡Zona {zone_name} creada exitosamente con {locations_added} ubicaciones!")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Ya existe una zona con ese nombre")
    
    # Location Management
    with st.expander("Agregar Nueva Ubicación"):
        # Get existing zones for the dropdown
        existing_locations = LocationDB.get_all_locations()
        existing_zones = sorted(list(set(loc['zone'] for loc in existing_locations)))
        
        if not existing_zones:
            st.warning("No hay zonas creadas. Por favor, cree una zona primero.")
            st.stop()
        
        zone = st.selectbox("Zona", options=existing_zones)
        
        # Pasillo range inputs
        col1, col2 = st.columns(2)
        with col1:
            aisle_start = st.text_input("Pasillo Inicio", key="aisle_start")
        with col2:
            aisle_end = st.text_input("Pasillo Fin", key="aisle_end")
        
        # Estante range inputs
        col3, col4 = st.columns(2)
        with col3:
            shelf_start = st.text_input("Estante Inicio", key="shelf_start")
        with col4:
            shelf_end = st.text_input("Estante Fin", key="shelf_end")
        
        # Posición range inputs
        col5, col6 = st.columns(2)
        with col5:
            position_start = st.text_input("Posición Inicio", key="position_start")
        with col6:
            position_end = st.text_input("Posición Fin", key="position_end")
        
        if st.button("Agregar Ubicaciones"):
            try:
                # Convert inputs to ranges
                if not aisle_start.isdigit() or (aisle_end and not aisle_end.isdigit()):
                    st.error("Los valores de Pasillo deben ser números enteros positivos")
                    st.stop()
                if not shelf_start.isdigit() or (shelf_end and not shelf_end.isdigit()):
                    st.error("Los valores de Estante deben ser números enteros positivos")
                    st.stop()
                if not position_start.isdigit() or (position_end and not position_end.isdigit()):
                    st.error("Los valores de Posición deben ser números enteros positivos")
                    st.stop()
                
                aisle_range = range(int(aisle_start), int(aisle_end) + 1) if aisle_end else [int(aisle_start)]
                shelf_range = range(int(shelf_start), int(shelf_end) + 1) if shelf_end else [int(shelf_start)]
                position_range = range(int(position_start), int(position_end) + 1) if position_end else [int(position_start)]
                
                # Create locations for all combinations
                locations_added = 0
                duplicates = 0
                for aisle in aisle_range:
                    for shelf in shelf_range:
                        for position in position_range:
                            try:
                                LocationDB.add_location(zone, str(aisle), str(shelf), str(position))
                                locations_added += 1
                            except sqlite3.IntegrityError:
                                duplicates += 1
                
                if locations_added > 0:
                    success_msg = f"¡{locations_added} ubicaciones agregadas exitosamente!"
                    if duplicates > 0:
                        success_msg += f" ({duplicates} ubicaciones duplicadas omitidas)"
                    st.success(success_msg)
                else:
                    st.warning("No se pudieron agregar ubicaciones. Todas las ubicaciones ya existen.")
            except ValueError:
                st.error("Por favor, ingrese valores numéricos válidos para los rangos")
    
    # Visual Layout
    st.subheader("Disposición del Almacén")
    
    # Custom CSS for the warehouse layout
    st.markdown("""
    <style>
    .warehouse-grid {
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 20px;
        background: #f8f9fa;
        border-radius: 10px;
    }
    .zone-header {
        font-size: 1.2em;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 10px;
    }
    .aisle-container {
        display: flex;
        gap: 10px;
        margin-bottom: 15px;
    }
    .aisle-label {
        writing-mode: vertical-lr;
        text-orientation: mixed;
        padding: 10px 5px;
        background: #2c3e50;
        color: white;
        border-radius: 5px;
        text-align: center;
    }
    .shelf-container {
        display: flex;
        flex-direction: column;
        gap: 5px;
    }
    .shelf {
        padding: 8px;
        background: #3498db;
        color: white;
        border-radius: 5px;
        text-align: center;
        min-width: 100px;
    }
    .shelf.empty {
        background: #ecf0f1;
        color: #7f8c8d;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Get all locations and organize them by zone
    locations = LocationDB.get_all_locations()
    if locations:
        # Group locations by zone
        zones = {}
        for loc in locations:
            zone = loc['zone']
            if zone not in zones:
                zones[zone] = {}
            
            # Validate that aisle, shelf, and position are numeric
            if not (loc['aisle'].isdigit() and loc['shelf'].isdigit() and loc['position'].isdigit()):
                continue
            
            aisle = int(loc['aisle'])
            if aisle not in zones[zone]:
                zones[zone][aisle] = {}
            
            shelf = int(loc['shelf'])
            if shelf not in zones[zone][aisle]:
                zones[zone][aisle][shelf] = []
            
            zones[zone][aisle][shelf].append(int(loc['position']))
        
        # Display each zone with modern layout
        for zone_name, zone_data in zones.items():
            st.markdown(f"<div class='warehouse-grid'>", unsafe_allow_html=True)
            st.markdown(f"<div class='zone-header'>Zona: {zone_name}</div>", unsafe_allow_html=True)
            
            max_aisle = max(zone_data.keys()) if zone_data else 0
            max_shelf = max(max(aisle.keys()) for aisle in zone_data.values()) if zone_data else 0
            
            # Create a container for the entire zone layout
            st.markdown("<div style='display: flex; gap: 20px;'>", unsafe_allow_html=True)
            
            # Display aisles and shelves
            for aisle in range(max_aisle + 1):
                aisle_html = f"<div class='aisle-container'><div class='aisle-label'>Pasillo {aisle + 1}</div><div class='shelf-container'>"
                
                for shelf in range(max_shelf + 1):
                    if aisle in zone_data and shelf in zone_data[aisle]:
                        positions = sorted(zone_data[aisle][shelf])
                        positions_str = ', '.join(map(lambda x: str(x + 1), positions))
                        aisle_html += f"<div class='shelf'>Estante {shelf + 1}<br>Posiciones: {positions_str}</div>"
                    else:
                        aisle_html += f"<div class='shelf empty'>Estante {shelf + 1}<br>Sin posiciones</div>"
                
                aisle_html += "</div></div>"
                st.markdown(aisle_html, unsafe_allow_html=True)
            
            st.markdown("</div></div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

    
    # Display locations with actions
    st.subheader("Gestión de Ubicaciones")
    
    # Add button to clear all locations
    if st.button("Borrar Todas las Ubicaciones", key="clear_all_locations_btn"):
        if st.warning("¿Está seguro de que desea borrar todas las ubicaciones? Esta acción no se puede deshacer."):
            LocationDB.clear_all_locations()
            st.success("Todas las ubicaciones han sido borradas")
            st.rerun()
    
    locations = LocationDB.get_all_locations()
    if locations:
        # Group locations hierarchically
        zones = {}
        for loc in locations:
            zone = loc['zone']
            aisle = loc['aisle']
            shelf = loc['shelf']
            
            if zone not in zones:
                zones[zone] = {}
            if aisle not in zones[zone]:
                zones[zone][aisle] = {}
            if shelf not in zones[zone][aisle]:
                zones[zone][aisle][shelf] = []
            zones[zone][aisle][shelf].append(loc)
        
        # Display hierarchical structure with a single expander per zone
        for zone_name, zone_data in zones.items():
            with st.expander(f"🏭 Zona: {zone_name}"):
                for aisle_name, aisle_data in zone_data.items():
                    st.markdown(f"### 🚶 Pasillo: {aisle_name}")
                    
                    for shelf_name, shelf_locations in aisle_data.items():
                        st.markdown(f"#### 📚 Estante: {shelf_name}")
                        
                        for loc in shelf_locations:
                            with st.container():
                                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                                
                                with col1:
                                    st.write(f"📍 Posición: {loc['position']}")
                                
                                with col2:
                                    if st.button("✏️ Editar", key=f"edit_{loc['location_id']}"):
                                        st.session_state['editing_location'] = loc['location_id']
                                
                                with col3:
                                    if st.button("🗑️ Eliminar", key=f"delete_{loc['location_id']}"):
                                        if st.warning("¿Está seguro de que desea eliminar esta ubicación?"):
                                            LocationDB.delete_location(loc['location_id'])
                                            st.success("Ubicación eliminada exitosamente")
                                            st.rerun()
                                
                                with col4:
                                    if st.button("📋 Duplicar", key=f"duplicate_{loc['location_id']}"):
                                        new_id = LocationDB.duplicate_location(loc['location_id'])
                                        if new_id:
                                            st.success("Ubicación duplicada exitosamente")
                                            st.rerun()
                                
                                # Edit form
                                if 'editing_location' in st.session_state and st.session_state['editing_location'] == loc['location_id']:
                                    with st.form(key=f"edit_form_{loc['location_id']}"):
                                        new_zone = st.text_input("Zona", value=loc['zone'])
                                        new_aisle = st.text_input("Pasillo", value=loc['aisle'])
                                        new_shelf = st.text_input("Estante", value=loc['shelf'])
                                        new_position = st.text_input("Posición", value=loc['position'])
                                        
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            if st.form_submit_button("Guardar"):
                                                LocationDB.update_location(loc['location_id'], new_zone, new_aisle, new_shelf, new_position)
                                                st.session_state.pop('editing_location')
                                                st.success("Ubicación actualizada exitosamente")
                                                st.rerun()
                                        with col2:
                                            if st.form_submit_button("Cancelar"):
                                                st.session_state.pop('editing_location')
                                                st.rerun()
                                
                                st.markdown("---")

    