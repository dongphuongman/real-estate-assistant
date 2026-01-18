from data.schemas import Property, PropertyCollection
from ui.geo_viz import create_price_heatmap
import folium


def test_create_price_heatmap_empty_collection_returns_map():
    coll = PropertyCollection(properties=[], total_count=0)
    m = create_price_heatmap(coll, center_city="Warsaw", jitter=False)
    assert isinstance(m, folium.Map)


def test_create_price_heatmap_with_properties_returns_map():
    props = [
        Property(city="Warsaw", latitude=52.23, longitude=21.01, price=5000),
        Property(city="Krakow", latitude=50.06, longitude=19.94, price=4000),
        Property(city="Gdansk", latitude=54.35, longitude=18.64, price=3500),
    ]
    coll = PropertyCollection(properties=props, total_count=len(props))
    m = create_price_heatmap(coll, center_city="Warsaw", jitter=False)
    assert isinstance(m, folium.Map)
