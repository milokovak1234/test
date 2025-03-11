import streamlit as st
import pandas as pd
from database.db_utils import ProductDB, LocationDB, OrderDB, get_db_connection, ProcessHistoryDB
from database.location_manager import LocationManager
from datetime import datetime

def render_recepcion_ordenes():
    st.title("📦 Recepción de Órdenes de Compra")
    
    # Initialize session state for form data
    if 'purchase_order_items' not in st.session_state:
        st.session_state.purchase_order_items = []
    if 'current_po_number' not in st.session_state:
        st.session_state.current_po_number = None
    
    # Purchase Order Header Form
    with st.form("po_header_form"):
        st.subheader("Datos de la Orden de Compra")
        col1, col2 = st.columns(2)
        
        with col1:
            po_number = st.text_input("Número de Orden", key="po_number")
            supplier = st.text_input("Proveedor", key="supplier")
        
        with col2:
            delivery_date = st.date_input("Fecha de Entrega", key="delivery_date")
            document_type = st.selectbox(
                "Tipo de Documento",
                ["Orden de Compra", "Remito", "Factura"],
                key="document_type"
            )
        
        notes = st.text_area("Observaciones", key="notes")
        submit_header = st.form_submit_button("Iniciar Recepción")
    
    if submit_header and po_number:
        # Check if order number already exists using context manager
        with get_db_connection() as conn:
            existing_order = conn.execute('SELECT order_id FROM orders WHERE order_number = ?', (po_number,)).fetchone()
        
        if existing_order:
            st.warning(f"Ya existe una orden con el número {po_number}.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Eliminar orden existente"):
                    try:
                        OrderDB.delete_order(existing_order[0])
                        
                        # Log the deletion process
                        ProcessHistoryDB.log_process(
                            operation_type="Recepción",
                            sub_operation="Eliminación de Orden",
                            status="Completado",
                            details=f"Orden {po_number} eliminada"
                        )
                        
                        st.success(f"Orden {po_number} eliminada exitosamente")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al eliminar la orden: {str(e)}")
            with col2:
                if st.button("Sobreescribir orden existente"):
                    st.session_state.current_po_number = po_number
                    
                    # Log the overwrite initiation
                    ProcessHistoryDB.log_process(
                        operation_type="Recepción",
                        sub_operation="Inicio de Sobreescritura",
                        status="En Proceso",
                        details=f"Iniciando sobreescritura de orden {po_number}"
                    )
                    
                    st.success(f"Orden de compra {po_number} iniciada para sobreescritura")
                    st.rerun()
        else:
            st.session_state.current_po_number = po_number
            
            # Log the new order initiation
            ProcessHistoryDB.log_process(
                operation_type="Recepción",
                sub_operation="Inicio de Orden",
                status="En Proceso",
                details=f"Nueva orden {po_number} iniciada"
            )
            
            st.success(f"Orden de compra {po_number} iniciada correctamente")
            st.rerun()
    
    # Display Product Selection and Reception Form if PO is initiated
    if st.session_state.current_po_number:
        # Add a button to navigate to location assignment outside the form
        if st.session_state.purchase_order_items:
            if st.button("Ir a Asignación de Ubicaciones", key="goto_location_assignment"):
                st.switch_page("_asignar_ubicaciones.py")
                
        with st.form("po_items_form"):
            st.subheader("Recepción de Productos")
            st.subheader("Agregar Productos")
            
            # Get all products for selection
            products = ProductDB.get_all_products()
            product_options = {f"{p['sku']} - {p['name']}": p for p in products}
            
            col1, col2 = st.columns(2)
            with col1:
                selected_product = st.selectbox(
                    "Seleccionar Producto",
                    options=list(product_options.keys()),
                    key="product_select"
                )
            
            with col2:
                quantity = st.number_input("Cantidad", min_value=1, value=1, key="quantity")
            
            # Get available reception locations
            reception_locations = LocationManager.get_locations_by_zone("Recepción")
            location_options = [f"{loc['aisle']}-{loc['shelf']}-{loc['position']}" for loc in reception_locations]
            
            col3, col4 = st.columns(2)
            with col3:
                selected_location = st.selectbox(
                    "Ubicación de Recepción",
                    options=location_options,
                    key="location_select"
                )
            
            with col4:
                quality_status = st.selectbox(
                    "Estado de Calidad",
                    ["Pendiente", "Aprobado", "Rechazado"],
                    key="quality_status"
                )
            
            submit_item = st.form_submit_button("Agregar Producto")
        
        if submit_item and selected_product:
            product = product_options[selected_product]
            item = {
                "sku": product['sku'],
                "name": product['name'],
                "quantity": quantity,
                "location": selected_location,
                "quality_status": quality_status,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.session_state.purchase_order_items.append(item)
            
            # Log the product addition
            ProcessHistoryDB.log_process(
                operation_type="Recepción",
                sub_operation="Agregar Producto",
                status="Completado",
                details=f"Producto {product['name']} (SKU: {product['sku']}) agregado a orden {st.session_state.current_po_number}"
            )
            
            st.success(f"Producto {product['name']} agregado correctamente")
            st.rerun()
        
        # Display current items in the order
        if st.session_state.purchase_order_items:
            st.subheader("Productos en la Orden")
            items_df = pd.DataFrame(st.session_state.purchase_order_items)
            st.dataframe(items_df)
            
            if st.button("Finalizar Recepción"):
                try:
                    with get_db_connection() as conn:
                        # Get existing order ID if overwriting
                        existing_order = conn.execute('SELECT order_id FROM orders WHERE order_number = ?', 
                                                     (st.session_state.current_po_number,)).fetchone()
                        
                        if existing_order:
                            # Delete existing order items
                            OrderDB.delete_order(existing_order[0])
                            order_id = existing_order[0]
                        else:
                            # Get order type for inbound orders
                            order_types = OrderDB.get_all_order_types()
                            order_type_id = next((ot['type_id'] for ot in order_types if ot['code'] == 'INBOUND'), None)
                            if not order_type_id:
                                raise ValueError("Order type 'INBOUND' not found")
                            
                            order_id = OrderDB.create_order(
                                order_number=st.session_state.current_po_number,
                                type_id=order_type_id,
                                status="completed"
                            )
                        
                        # Add items to order and update inventory
                        for item in st.session_state.purchase_order_items:
                            product = next(p for p in products if p['sku'] == item['sku'])
                            OrderDB.add_order_items(order_id, [{
                                'product_id': product['product_id'],
                                'quantity': item['quantity']
                            }])
                            
                            # Update product stock
                            ProductDB.update_stock(product['product_id'], item['quantity'])
                    
                    # Log the successful completion
                    ProcessHistoryDB.log_process(
                        operation_type="Recepción",
                        sub_operation="Finalización de Orden",
                        status="Completado",
                        details=f"Orden {st.session_state.current_po_number} completada con {len(st.session_state.purchase_order_items)} productos"
                    )
                    
                    st.success("Recepción finalizada exitosamente")
                    # Clear session state
                    st.session_state.purchase_order_items = []
                    st.session_state.current_po_number = None
                    st.rerun()
                
                except Exception as e:
                    # Log the error
                    ProcessHistoryDB.log_process(
                        operation_type="Recepción",
                        sub_operation="Error en Finalización",
                        status="Error",
                        details=f"Error en orden {st.session_state.current_po_number}: {str(e)}"
                    )
                    st.error(f"Error al procesar la recepción: {str(e)}")
            
            if st.button("Cancelar Recepción"):
                # Log the cancellation
                ProcessHistoryDB.log_process(
                    operation_type="Recepción",
                    sub_operation="Cancelación de Orden",
                    status="Cancelado",
                    details=f"Orden {st.session_state.current_po_number} cancelada"
                )
                
                st.session_state.purchase_order_items = []
                st.session_state.current_po_number = None
                st.rerun()

if __name__ == "__main__":
    render_recepcion_ordenes()