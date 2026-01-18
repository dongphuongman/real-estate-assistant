from data.schemas import Property, PropertyCollection
from ui.geo_viz import create_city_overview_map
import folium


def test_create_city_overview_map_empty_collection_returns_map():
    coll = PropertyCollection(properties=[], total_count=0)
    m = create_city_overview_map(coll)
    assert isinstance(m, folium.Map)


def test_create_city_overview_map_with_properties_returns_map():
    # Generate simple dataset across multiple cities
    cities = ["Warsaw", "Krakow", "Wroclaw", "Poznan"]
    props = []
    for i, city in enumerate(cities, 1):
        props.append(
            Property(
                city=city,
                price=3000 + i * 500,
                rooms=1 + (i % 3),
                latitude=None,
                longitude=None,
            )
        )
    coll = PropertyCollection(properties=props, total_count=len(props))
    m = create_city_overview_map(coll)
    assert isinstance(m, folium.Map)
