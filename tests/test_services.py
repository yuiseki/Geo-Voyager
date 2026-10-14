

def test_the_overpass_description_says_how_to_select_one_element_type():
    from geo_voyager.services import load_service_graph
    description = load_service_graph().get('overpass').description
    assert 'nwr はノード・ウェイ・リレーションを合わせて選ぶ' in description and 'ノードだけなら node' in description


def test_the_geosparql_description_says_its_wards_reach_into_the_sea():
    # Measured 2026-10-14: the OSM ward areas include Tokyo Bay, so 大田区 and 江戸川区 touch at sea only; with the
    # land areas of jp-admin they are about 6 km apart. A Critic called that pair wrong and the Goal was lost.
    from geo_voyager.services import load_service_graph
    description = load_service_graph().get('yuisekin-geosparql').description
    assert '海' in description and '大田区と江戸川区' in description
