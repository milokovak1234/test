import os
import subprocess
import socket
from database.db_utils import init_database
from dotenv import load_dotenv

def get_local_ip():
    try:
        # Get the local machine's hostname
        hostname = socket.gethostname()
        # Get the local IP address
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return "localhost"

def main():
    # Load environment variables
    load_dotenv()

    # Initialize the database
    print("Initializing database...")
    init_database()
    
    # Get the absolute path to the gestion_parametros.py file
    app_path = os.path.join(os.path.dirname(__file__), 'gestion_parametros.py')
    
    # Get local IP address
    local_ip = get_local_ip()
    
    # Set Streamlit configuration for camera access
    os.environ['STREAMLIT_SERVER_ENABLE_CAMERA'] = 'true'
    os.environ['STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION'] = 'false'
    os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
    
    # Start the Streamlit server
    print("Starting WMS Lite server...")
    print(f"\nServer is running on:")
    print(f"Local URL: http://localhost:8501")
    print(f"Network URL: http://{local_ip}:8501")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        subprocess.run(['streamlit', 'run', app_path], check=True)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")

if __name__ == '__main__':
    main()