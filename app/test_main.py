from app.main import Receipt, calculate_points
from fastapi.testclient import TestClient

from .main import app

client = TestClient(app)

receipt_target = {
    "retailer": "Target",
    "purchaseDate": "2022-01-01",
    "purchaseTime": "13:01",
    "items": [
        {"shortDescription": "Mountain Dew 12PK", "price": "6.49"},
        {"shortDescription": "Emils Cheese Pizza", "price": "12.25"},
        {"shortDescription": "Knorr Creamy Chicken", "price": "1.26"},
        {"shortDescription": "Doritos Nacho Cheese", "price": "3.35"},
        {"shortDescription": "   Klarbrunn 12-PK 12 FL OZ  ", "price": "12.00"},
    ],
    "total": "35.35",
}

receipt_mm_market = {
    "retailer": "M&M Corner Market",
    "purchaseDate": "2022-03-20",
    "purchaseTime": "14:33",
    "items": [
        {"shortDescription": "Gatorade", "price": "2.25"},
        {"shortDescription": "Gatorade", "price": "2.25"},
        {"shortDescription": "Gatorade", "price": "2.25"},
        {"shortDescription": "Gatorade", "price": "2.25"},
    ],
    "total": "9.00",
}


def test_points_one():

    receipt1 = Receipt(**receipt_target)
    assert calculate_points(receipt1) == 28


def test_points_two():

    receipt2 = Receipt(**receipt_mm_market)
    assert calculate_points(receipt2) == 109


def test_read_points_no_receipt():
    response = client.get("/receipts/f04602ee-2548-4863-80b7-f30683210797/points")
    assert response.status_code == 404


def test_process_valid_receipt():
    response = client.post("/receipts/process", json=receipt_target)
    assert response.status_code == 200


def test_process_valid_receipt_and_points():
    response = client.post("/receipts/process", json=receipt_target)
    assert response.status_code == 200
    receipt_id = response.json()["id"]

    response = client.get(f"/receipts/{receipt_id}/points")
    assert response.status_code == 200
    assert response.json() == {"points": 28}


def test_process_valid_receipt2_and_points():
    response = client.post("/receipts/process", json=receipt_mm_market)
    assert response.status_code == 200
    receipt_id = response.json()["id"]

    response = client.get(f"/receipts/{receipt_id}/points")
    assert response.status_code == 200
    assert response.json() == {"points": 109}


# New test receipt with edge cases
receipt_edge_case = {
    "retailer": "  Walmart  ",  # Extra spaces
    "purchaseDate": "2022-02-28",  # Last day of month
    "purchaseTime": "16:00",  # Round hour
    "items": [
        {"shortDescription": "Item", "price": "10.00"},  # Round dollar amount
    ],
    "total": "10.00",
}


def test_empty_items_list():
    receipt_empty = {
        "retailer": "Shop",
        "purchaseDate": "2022-01-01",
        "purchaseTime": "12:00",
        "items": [],
        "total": "0.00",
    }
    response = client.post("/receipts/process", json=receipt_empty)
    assert response.status_code == 400


def test_edge_case_receipt_points():
    response = client.post("/receipts/process", json=receipt_edge_case)
    assert response.status_code == 200
    receipt_id = response.json()["id"]

    response = client.get(f"/receipts/{receipt_id}/points")
    assert response.status_code == 200
    points = response.json()["points"]
    assert isinstance(points, int)
    assert points >= 0


def test_invalid_receipt_format():
    invalid_receipt = {
        "retailer": "Shop",
        "purchaseDate": "invalid-date",  # Invalid date format
    }
    response = client.post("/receipts/process", json=invalid_receipt)
    assert response.status_code == 400


def test_malformed_receipt_id():
    response = client.get("/receipts/invalid-uuid-format/points")
    assert response.status_code == 404


def test_duplicate_process_receipt():
    # Process same receipt twice
    first_response = client.post("/receipts/process", json=receipt_edge_case)
    assert first_response.status_code == 200
    first_id = first_response.json()["id"]

    second_response = client.post("/receipts/process", json=receipt_edge_case)
    assert second_response.status_code == 200
    second_id = second_response.json()["id"]

    # Should generate different IDs
    assert first_id != second_id


# Test data following OpenAPI schema patterns
receipt_schema_test = {
    "retailer": "Test-Store&Market",  # Testing pattern "^[\\w\\s\\-&]+$"
    "purchaseDate": "2023-12-31",
    "purchaseTime": "23:59",
    "items": [
        {"shortDescription": "Test-Item-1", "price": "99.99"},
        {"shortDescription": "Test Item 2", "price": "0.01"},
    ],
    "total": "100.00",
}


def test_retailer_pattern():
    invalid_retailers = [
        {
            "retailer": "Store!",
            "purchaseDate": "2023-01-01",
            "purchaseTime": "12:00",
            "items": [{"shortDescription": "Item", "price": "1.00"}],
            "total": "1.00",
        },
        {
            "retailer": "Store@Market",
            "purchaseDate": "2023-01-01",
            "purchaseTime": "12:00",
            "items": [{"shortDescription": "Item", "price": "1.00"}],
            "total": "1.00",
        },
    ]
    for receipt in invalid_retailers:
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 400


def test_price_pattern():
    invalid_prices = [
        {"shortDescription": "Item", "price": "1.0"},  # Missing decimal
        {"shortDescription": "Item", "price": "1.000"},  # Extra decimal
        {"shortDescription": "Item", "price": "1"},  # No decimals
        {"shortDescription": "Item", "price": ".99"},  # Missing leading zero
    ]
    for item in invalid_prices:
        test_receipt = receipt_schema_test.copy()
        test_receipt["items"] = [item]
        test_receipt["total"] = item["price"]
        response = client.post("/receipts/process", json=test_receipt)
        assert response.status_code == 400


def test_time_format():
    invalid_times = ["24:00", "12:60", "1:00", "12:00 AM"]
    for time in invalid_times:
        test_receipt = receipt_schema_test.copy()
        test_receipt["purchaseTime"] = time
        response = client.post("/receipts/process", json=test_receipt)
        assert response.status_code == 400


def test_date_format():
    invalid_dates = ["2023/01/01", "01-01-2023", "2023-13-01", "2023-01-32"]
    for date in invalid_dates:
        test_receipt = receipt_schema_test.copy()
        test_receipt["purchaseDate"] = date
        response = client.post("/receipts/process", json=test_receipt)
        assert response.status_code == 400


def test_required_fields():
    required_fields = ["retailer", "purchaseDate", "purchaseTime", "items", "total"]
    base_receipt = receipt_schema_test.copy()

    for field in required_fields:
        test_receipt = base_receipt.copy()
        del test_receipt[field]
        response = client.post("/receipts/process", json=test_receipt)
        assert response.status_code == 400


def test_valid_id_pattern():
    response = client.post("/receipts/process", json=receipt_schema_test)
    assert response.status_code == 200
    id_pattern = response.json()["id"]
    assert " " not in id_pattern  # Matches pattern "^\\S+$"


def test_minimum_items():
    test_receipt = receipt_schema_test.copy()
    test_receipt["items"] = []
    response = client.post("/receipts/process", json=test_receipt)
    assert response.status_code == 400
