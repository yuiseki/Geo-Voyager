

def test_the_overpass_description_says_how_to_select_one_element_type():
    from geo_voyager.services import load_service_graph
    description = load_service_graph().get('overpass').description
    assert 'nwr はノード・ウェイ・リレーションを合わせて選ぶ' in description and 'ノードだけなら node' in description
