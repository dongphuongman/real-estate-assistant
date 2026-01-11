
from ui.price_charts import create_price_comparison_chart

def test_create_price_comparison_chart_exists():
    # This should fail if the function is missing or import error
    assert callable(create_price_comparison_chart)
