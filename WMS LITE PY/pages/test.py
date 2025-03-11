import cv2
import numpy as np
import streamlit as st

import streamlit as st
from streamlit_webrtc import webrtc_streamer

"# Streamlit camera input live Demo"
"## Try holding a qr code in front of your webcam"

image = st.camera_input("Take a picture")

if image is not None:
    st.image(image)
    bytes_data = image.getvalue()
    cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

    detector = cv2.QRCodeDetector()

    data, bbox, straight_qrcode = detector.detectAndDecode(cv2_img)

    if data:
        st.write("# Found QR code")
        st.write(data)
        with st.expander("Show details"):
            st.write("BBox:", bbox)
            st.write("Straight QR code:", straight_qrcode)