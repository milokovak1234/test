from typing import List, Optional
import streamlit as st
from .db_utils import get_db_connection, LocationDB
from .zone_manager import ZoneManager

class LocationManager:
    @staticmethod
    def get_locations_by_zone(zone: str) -> List[dict]:
        with get_db_connection() as conn:
            locations = conn.execute(
                'SELECT * FROM locations WHERE zone = ?',
                (zone,)
            ).fetchall()
            return [dict(loc) for loc in locations]
    
    @staticmethod
    def get_available_zones() -> List[str]:
        with get_db_connection() as conn:
            zones = conn.execute(
                'SELECT DISTINCT zone FROM locations'
            ).fetchall()
            return [zone[0] for zone in zones]
    
    @staticmethod
    def create_location_in_zone(zone: str, aisle: str, shelf: str, position: str) -> Optional[int]:
        """Create a new location in the specified zone"""
        try:
            with get_db_connection() as conn:
                location_id = LocationDB.add_location(zone=zone, aisle=aisle, shelf=shelf, position=position)
                if location_id:
                    return location_id
                st.warning(f"Failed to create location in zone {zone}")
                return None
        except Exception as e:
            st.error(f"Error creating location: {str(e)}")
            return None
    
    @staticmethod
    def validate_zone_for_order_type(zone: str, order_type_code: str, is_source: bool = False) -> bool:
        """Validate if a zone is allowed for a specific order type
        Args:
            zone: The zone to validate
            order_type_code: The order type code to check against
            is_source: If True, checks against allowed source zones, otherwise checks destination zones
        Returns:
            bool: True if the zone is valid for the order type, False otherwise
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Get both source and destination zones for the order type
            order_type = cursor.execute(
                'SELECT allowed_source_zones, allowed_destination_zones FROM order_types WHERE code = ?',
                (order_type_code,)
            ).fetchone()
            
            if not order_type:
                return False

            # For stock entry orders, we need to ensure destination zones are properly handled
            if order_type_code == 'STOCK_IN' and not is_source:
                # For stock entry, any zone can be a destination if it has locations
                zones_to_check = '*'
            else:
                # For other cases, use the configured zones
                zones_to_check = order_type[0] if is_source else order_type[1]
                if not zones_to_check:
                    # If no zones are specified, allow any zone
                    zones_to_check = '*'

            # If zones_to_check is '*', allow any zone
            if zones_to_check == '*' or zone in zones_to_check.split(','):
                # Check if the zone has any locations
                zone_locations_count = ZoneManager.get_zone_locations_count(zone)
                if zone_locations_count == 0:
                    # Create default grid of locations for the zone
                    location_ids = ZoneManager.create_zone_with_locations(zone)
                    return len(location_ids) > 0
                return True
            
            return False
        finally:
            conn.close()