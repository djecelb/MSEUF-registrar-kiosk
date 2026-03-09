from app import calculate_fee
def test_fee():
    assert calculate_fee(1,1) == 220