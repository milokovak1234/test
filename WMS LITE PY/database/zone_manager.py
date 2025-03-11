from typing import List, Optional
import streamlit as st
from .db_utils import get_db_connection, LocationDB

class ZoneManager:
    @staticmethod
    def create_zone_with_locations(zone: str, num_aisles: int = 3, num_shelves: int = 4, num_positions: int = 5) -> List[int]:
        """Create a new zone with a grid of locations"""
        location_ids = []
        try:
            with get_db_connection() as conn:
                for aisle in range(1, num_aisles + 1):
                    for shelf in range(1, num_shelves + 1):
                        for position in range(1, num_positions + 1):
                            try:
                                aisle_str = str(aisle).zfill(2)
                                shelf_str = str(shelf).zfill(2)
                                position_str = str(position).zfill(2)
                                
                                location_id = LocationDB.add_location(
                                    zone=zone,
                                    aisle=aisle_str,
                                    shelf=shelf_str,
                                    position=position_str
                                )
                                if location_id:
                                    location_ids.append(location_id)
                                else:
                                    st.warning(f"Failed to create location {aisle_str}-{shelf_str}-{position_str} in zone {zone}")
                            except Exception as e:
                                st.warning(f"Error creating location {aisle_str}-{shelf_str}-{position_str}: {str(e)}")
                                continue
                return location_ids
        except Exception as e:
            st.error(f"Error creating zone locations: {str(e)}")
            return []
    
    @staticmethod
    def get_zone_locations_count(zone: str) -> int:
        """Get the number of locations in a zone"""
        with get_db_connection() as conn:
            count = conn.execute(
                'SELECT COUNT(*) FROM locations WHERE zone = ?',
                (zone,)
            ).fetchone()[0]
            return count