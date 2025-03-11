from database.db_utils import OrderDB, init_database

# Initialize the database first
print("Initializing database...")
init_database()

# Create basic order types
order_types = [
    {
        "code": "INBOUND",
        "name": "Ingreso de Stock",
        "description": "Recepción de mercadería en el almacén",
        "requires_destination_location": True,
        "affects_stock": True,
        "allowed_destination_zones": "Recepción,Almacenamiento"
    },
    {
        "code": "OUTBOUND",
        "name": "Egreso de Stock",
        "description": "Salida de mercadería del almacén",
        "requires_source_location": True,
        "affects_stock": True,
        "allowed_source_zones": "Picking,Despacho,Almacenamiento"
    },
    {
        "code": "TRANSFER",
        "name": "Movimiento de Depósito",
        "description": "Transferencia de mercadería entre ubicaciones",
        "requires_source_location": True,
        "requires_destination_location": True,
        "affects_stock": False,
        "allowed_source_zones": "Almacenamiento,Picking,Cross-Docking",
        "allowed_destination_zones": "Almacenamiento,Picking,Cross-Docking"
    },
    {
        "code": "ZONE_MOVE",
        "name": "Movimiento de Zona",
        "description": "Reubicación de mercadería entre zonas",
        "requires_source_location": True,
        "requires_destination_location": True,
        "affects_stock": False,
        "allowed_source_zones": "Almacenamiento,Picking,Cross-Docking,Control de Calidad,Cuarentena",
        "allowed_destination_zones": "Almacenamiento,Picking,Cross-Docking,Control de Calidad,Cuarentena"
    }
]

print("Creating order types...")
# Add order types to database
for order_type in order_types:
    try:
        OrderDB.add_order_type(
            code=order_type["code"],
            name=order_type["name"],
            description=order_type["description"],
            requires_source_location=order_type.get("requires_source_location", False),
            requires_destination_location=order_type.get("requires_destination_location", False),
            affects_stock=order_type.get("affects_stock", True),
            allowed_source_zones=order_type.get("allowed_source_zones"),
            allowed_destination_zones=order_type.get("allowed_destination_zones")
        )
        print(f"Created order type: {order_type['name']}")
    except Exception as e:
        print(f"Error creating order type {order_type['code']}: {str(e)}")

print("\nOrder types initialization completed!")