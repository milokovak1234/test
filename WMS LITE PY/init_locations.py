from database.location_manager import LocationManager

def initialize_inbound_locations():
    # Define zones for inbound orders
    inbound_zones = ['Recepción', 'Almacenamiento']
    
    # Initial locations for each zone
    initial_locations = {
        'Recepción': [
            {'aisle': 'R1', 'shelf': '01', 'positions': ['A', 'B', 'C', 'D']},
            {'aisle': 'R2', 'shelf': '01', 'positions': ['A', 'B', 'C', 'D']}
        ],
        'Almacenamiento': [
            {'aisle': 'A1', 'shelf': '01', 'positions': ['01', '02', '03', '04']},
            {'aisle': 'A1', 'shelf': '02', 'positions': ['01', '02', '03', '04']},
            {'aisle': 'A2', 'shelf': '01', 'positions': ['01', '02', '03', '04']},
            {'aisle': 'A2', 'shelf': '02', 'positions': ['01', '02', '03', '04']}
        ]
    }
    
    created_locations = []
    
    # Create locations for each zone
    for zone in inbound_zones:
        print(f"\nCreating locations for zone: {zone}")
        zone_locations = initial_locations.get(zone, [])
        
        for loc in zone_locations:
            for pos in loc['positions']:
                try:
                    location_id = LocationManager.create_location_in_zone(
                        zone=zone,
                        aisle=loc['aisle'],
                        shelf=loc['shelf'],
                        position=pos
                    )
                    if location_id:
                        created_locations.append({
                            'id': location_id,
                            'zone': zone,
                            'aisle': loc['aisle'],
                            'shelf': loc['shelf'],
                            'position': pos
                        })
                        print(f"Created location: {zone} - {loc['aisle']}-{loc['shelf']}-{pos}")
                except Exception as e:
                    print(f"Error creating location: {str(e)}")
    
    print(f"\nCreated {len(created_locations)} locations for inbound operations")
    return created_locations

if __name__ == '__main__':
    print("Initializing locations for inbound operations...")
    initialize_inbound_locations()
    print("\nLocation initialization completed!")