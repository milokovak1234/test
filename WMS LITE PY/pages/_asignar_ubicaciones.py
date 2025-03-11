import streamlit as st
import cv2
from pyzbar.pyzbar import decode
import numpy as np
import io
from PIL import Image
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration
from database.db_utils import ProductDB, InventoryDB, LocationDB, ProcessHistoryDB
from database.location_manager import LocationManager
import av
import queue
import threading
import time

def render_asignar_ubicaciones():
    st.title("📍 Asignación de Ubicaciones")
    
    # Initialize session state
    if 'scanned_product' not in st.session_state:
        st.session_state.scanned_product = None
    if 'result_queue' not in st.session_state:
        st.session_state.result_queue = queue.Queue(maxsize=10)  # Limit queue size
    if 'camera_error' not in st.session_state:
        st.session_state.camera_error = None
    
    class BarcodeVideoTransformer(VideoTransformerBase):
        def __init__(self):
            self.result_queue = st.session_state.result_queue
            self.last_detection = None
            self.detection_cooldown = 1.0  # Cooldown in seconds
            self.last_detection_time = 0

        def transform(self, frame):
            try:
                current_time = time.time()
                img = frame.to_ndarray(format="bgr24")
                
                # Only process frame if cooldown has elapsed
                if current_time - self.last_detection_time >= self.detection_cooldown:
                    # Convert to grayscale
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    
                    # Apply image processing to improve barcode detection
                    gray = cv2.GaussianBlur(gray, (5, 5), 0)
                    gray = cv2.adaptiveThreshold(
                        gray, 255,
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY,
                        11, 2
                    )
                    
                    # Detect barcodes
                    barcodes = decode(gray)
                    
                    for barcode in barcodes:
                        try:
                            # Extract barcode data
                            barcode_data = barcode.data.decode('utf-8')
                            
                            # Draw rectangle and text
                            points = barcode.polygon
                            if points:
                                pts = np.array(points, np.int32)
                                pts = pts.reshape((-1, 1, 2))
                                cv2.polylines(img, [pts], True, (0, 255, 0), 2)
                            
                            # Add text with better visibility
                            x = barcode.rect.left
                            y = barcode.rect.top
                            cv2.rectangle(img, (x, y - 30), (x + 200, y), (0, 255, 0), -1)
                            cv2.putText(img, barcode_data, (x, y - 10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                            
                            # Only add to queue if it's a new detection
                            if barcode_data != self.last_detection:
                                try:
                                    self.result_queue.put_nowait(barcode_data)
                                    self.last_detection = barcode_data
                                    self.last_detection_time = current_time
                                except queue.Full:
                                    pass  # Queue is full, skip this detection
                        except Exception as e:
                            st.session_state.camera_error = f"Error processing barcode: {str(e)}"
                
                return img
            except Exception as e:
                st.session_state.camera_error = f"Error in transform: {str(e)}"
                return frame.to_ndarray(format="bgr24")

        def recv(self, frame):
            try:
                img = self.transform(frame)
                return av.VideoFrame.from_ndarray(img, format="bgr24")
            except Exception as e:
                st.session_state.camera_error = f"Error in recv: {str(e)}"
                return frame
    
    # Create two columns for barcode input methods
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Escanear Código de Barras")
        barcode = st.text_input("Ingrese o escanee el código de barras", key="barcode_input")
        if st.button("Buscar Producto"):
            if barcode:
                product = ProductDB.get_product_by_sku(barcode)
                if product:
                    st.session_state.scanned_product = product
                    st.success(f"Producto encontrado: {product['name']}")
                    
                    # Log the successful product scan
                    ProcessHistoryDB.log_process(
                        operation_type="Asignación de Ubicaciones",
                        sub_operation="Escaneo Manual",
                        status="Completado",
                        details=f"Producto escaneado: {product['name']} (SKU: {product['sku']})"
                    )
                else:
                    st.error("Producto no encontrado")
    
    with col2:
        st.subheader("Escanear con Cámara")
        
        # Add information about camera permissions
        st.info("Esta función requiere permisos de cámara. El escaneo comenzará automáticamente cuando se detecte un código de barras.")
        
        # WebRTC Configuration
        rtc_config = RTCConfiguration(
            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        )
        
        # Create WebRTC streamer
        webrtc_ctx = webrtc_streamer(
            key="barcode-scanner",
            video_transformer_factory=BarcodeVideoTransformer,
            rtc_configuration=rtc_config,
            media_stream_constraints={"video": True, "audio": False}
        )
        
        # Process results from the queue
        if webrtc_ctx.state.playing:
            try:
                while True:
                    barcode_data = st.session_state.result_queue.get_nowait()
                    st.write(f"Código detectado: {barcode_data}")
                    
                    # Look up product
                    product = ProductDB.get_product_by_sku(barcode_data)
                    if product and not st.session_state.scanned_product:
                        st.session_state.scanned_product = product
                        st.success(f"Producto encontrado: {product['name']}")
                        
                        # Log the successful camera scan
                        ProcessHistoryDB.log_process(
                            operation_type="Asignación de Ubicaciones",
                            sub_operation="Escaneo con Cámara",
                            status="Completado",
                            details=f"Producto escaneado: {product['name']} (SKU: {product['sku']})"
                        )
                        st.rerun()
                    elif not product:
                        st.error(f"No se encontró ningún producto con el código {barcode_data}")
            except queue.Empty:
                pass
    
    # Display product information and location assignment form if a product is scanned
    if st.session_state.scanned_product:
        st.subheader("Información del Producto")
        product = st.session_state.scanned_product
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**SKU:** {product['sku']}")
            st.write(f"**Nombre:** {product['name']}")
        with col2:
            st.write(f"**Categoría:** {product.get('category', 'N/A')}")
            st.write(f"**Stock Actual:** {product.get('current_stock', 0)}")
        
        st.subheader("Asignar Ubicación")
        with st.form("location_assignment_form"):
            # Get all zones for selection
            zones = LocationManager.get_available_zones()
            selected_zone = st.selectbox("Zona", zones)
            
            # Get locations for selected zone
            locations = LocationManager.get_locations_by_zone(selected_zone)
            location_options = [f"{loc['zone']}-{loc['aisle']}-{loc['shelf']}-{loc['position']}" for loc in locations]
            selected_location = st.selectbox("Ubicación", location_options)
            
            quantity = st.number_input("Cantidad", min_value=1, value=1)
            min_quantity = st.number_input("Cantidad Mínima", min_value=0, value=0)
            max_quantity = st.number_input("Cantidad Máxima", min_value=0, value=0)
            
            submit_button = st.form_submit_button("Asignar Ubicación")
            
            if submit_button:
                try:
                    # Get location_id from selected location
                    location_id = next(loc['location_id'] for loc in locations 
                                     if f"{loc['zone']}-{loc['aisle']}-{loc['shelf']}-{loc['position']}" == selected_location)
                    
                    # Add inventory record
                    inventory_id = InventoryDB.add_inventory(
                        product['product_id'],
                        location_id,
                        quantity,
                        min_quantity,
                        max_quantity
                    )
                    
                    if inventory_id:
                        st.success(f"Producto asignado exitosamente a la ubicación {selected_location}")
                        
                        # Log the successful assignment
                        ProcessHistoryDB.log_process(
                            operation_type="Asignación de Ubicaciones",
                            sub_operation="Asignación Completada",
                            status="Completado",
                            details=f"Producto {product['name']} (SKU: {product['sku']}) asignado a {selected_location}"
                        )
                        
                        # Clear the scanned product
                        st.session_state.scanned_product = None
                        st.rerun()
                    else:
                        st.error("Error al asignar la ubicación")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    
                    # Log the assignment error
                    ProcessHistoryDB.log_process(
                        operation_type="Asignación de Ubicaciones",
                        sub_operation="Error de Asignación",
                        status="Error",
                        details=f"Error al asignar ubicación: {str(e)}"
                    )
        
        if st.button("Cancelar"):
            st.session_state.scanned_product = None
            st.rerun()

# This code runs when the file is accessed directly as a Streamlit page
if __name__ == "__main__":
    render_asignar_ubicaciones()