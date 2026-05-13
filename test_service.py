from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from datetime import date

from app import app

client = TestClient(app)


def create_mock_connection():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


def test_health_check():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Rental API is running"
    }


@patch("app.get_connection")
def test_create_rental_success(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()
    mock_cursor.fetchone.return_value = [1]
    mock_get_connection.return_value = mock_conn

    payload = {
        "user_id": 1,
        "item_id": 10,
        "start_date": "2026-05-01",
        "end_date": "2026-05-05",
        "status": "active",
        "total_price": 100,
    }

    response = client.post("/rentals", json=payload)

    assert response.status_code == 200

    assert response.json() == {
        "message": "Rental created successfully",
        "id": 1,
    }

    mock_conn.commit.assert_called_once()


@patch("app.get_connection")
def test_get_rental_success(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()

    mock_cursor.fetchone.return_value = (
        1, 1, 10,
        date(2026, 5, 1),
        date(2026, 5, 5),
        "active",
        100,
    )

    mock_cursor.description = [
        ("id",),
        ("user_id",),
        ("item_id",),
        ("start_date",),
        ("end_date",),
        ("status",),
        ("total_price",),
    ]

    mock_get_connection.return_value = mock_conn

    response = client.get("/rentals/1")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 1
    assert data["user_id"] == 1
    assert data["item_id"] == 10


@patch("app.get_connection")
def test_get_rental_not_found(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()
    mock_cursor.fetchone.return_value = None
    mock_get_connection.return_value = mock_conn

    response = client.get("/rentals/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Rental not found"


@patch("app.get_connection")
def test_get_user_rentals(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()

    mock_cursor.fetchall.return_value = [
        (1, 1, 10, date(2026, 5, 1), date(2026, 5, 5), "active", 100)
    ]

    mock_cursor.description = [
        ("id",),
        ("user_id",),
        ("item_id",),
        ("start_date",),
        ("end_date",),
        ("status",),
        ("total_price",),
    ]

    mock_get_connection.return_value = mock_conn

    response = client.get("/rentals/user/1")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["user_id"] == 1


@patch("app.get_connection")
def test_update_rental_success(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()
    mock_cursor.fetchone.return_value = (1,)
    mock_get_connection.return_value = mock_conn

    payload = {"status": "completed"}

    response = client.put("/rentals/1", json=payload)

    assert response.status_code == 200

    assert response.json() == {
        "message": "Rental updated successfully"
    }

    mock_conn.commit.assert_called_once()


@patch("app.get_connection")
def test_update_rental_not_found(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()
    mock_cursor.fetchone.return_value = None
    mock_get_connection.return_value = mock_conn

    response = client.put("/rentals/999", json={"status": "completed"})

    assert response.status_code == 500


@patch("app.get_connection")
def test_update_rental_no_fields(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()
    mock_cursor.fetchone.return_value = (1,)
    mock_get_connection.return_value = mock_conn

    response = client.put("/rentals/1", json={})

    assert response.status_code == 500


@patch("app.get_connection")
def test_delete_rental_success(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()
    mock_cursor.rowcount = 1
    mock_get_connection.return_value = mock_conn

    response = client.delete("/rentals/1")

    assert response.status_code == 200

    assert response.json() == {
        "message": "Rental deleted successfully"
    }

    mock_conn.commit.assert_called_once()


@patch("app.get_connection")
def test_delete_rental_not_found(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()
    mock_cursor.rowcount = 0
    mock_get_connection.return_value = mock_conn

    response = client.delete("/rentals/999")

    assert response.status_code == 500


@patch("app.get_connection")
def test_calculate_rental_price_success(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()
    mock_cursor.fetchone.return_value = (
        date(2026, 5, 1),
        date(2026, 5, 6),
    )
    mock_get_connection.return_value = mock_conn

    response = client.post("/rentals/1/calculate")

    assert response.status_code == 200

    data = response.json()

    assert data["rental_days"] == 5
    assert data["daily_rate"] == 25
    assert data["calculated_price"] == 125

    mock_conn.commit.assert_called_once()


@patch("app.get_connection")
def test_calculate_rental_price_not_found(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()
    mock_cursor.fetchone.return_value = None
    mock_get_connection.return_value = mock_conn

    response = client.post("/rentals/999/calculate")

    assert response.status_code == 500
