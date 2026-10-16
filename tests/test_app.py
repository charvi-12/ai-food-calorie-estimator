from io import BytesIO

import pytest
from PIL import Image

from food_estimator import create_app


@pytest.fixture
def app(tmp_path):
    instance_path = tmp_path / "instance"
    app = create_app(
        {
            "TESTING": True,
            "INSTANCE_PATH": str(instance_path),
            "DATABASE": str(tmp_path / "test.sqlite3"),
            "UPLOAD_FOLDER": str(instance_path / "uploads"),
        }
    )
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def make_image():
    buffer = BytesIO()
    Image.new("RGB", (30, 20), color=(220, 180, 110)).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def test_dashboard_shows_indian_food_catalog_and_estimates(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Idli" in response.data
    assert b"Chapati" in response.data
    assert b"All values here are estimates" in response.data


def test_manual_food_can_be_estimated_and_saved_with_serving_size(client):
    response = client.post(
        "/analyze",
        data={"food_id": "idli"},
    )
    assert response.status_code == 200
    assert b"Idli" in response.data
    assert b"Manual estimate" in response.data

    response = client.post(
        "/meals",
        data={"food_id": "idli", "serving_grams": "150", "meal_type": "Breakfast"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Today's meals" in response.data
    assert b"219" in response.data


def test_unrecognized_ai_result_does_not_create_a_food_estimate(client, monkeypatch):
    from food_estimator import routes

    monkeypatch.setattr(
        routes,
        "recognize_food",
        lambda _image: {"status": "unrecognized", "candidates": []},
    )
    response = client.post(
        "/analyze",
        data={"image": (make_image(), "lunch.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert b"confidently match this image" in response.data
    assert b"YOUR MEAL ESTIMATE" not in response.data
    assert b"lunch.png" not in response.data


def test_supported_model_prediction_returns_nutrition_estimate(client, monkeypatch):
    from food_estimator import routes

    monkeypatch.setattr(
        routes,
        "recognize_food",
        lambda _image: {
            "status": "identified",
            "food_id": "fried_rice",
            "confidence": 0.91,
            "candidates": [{"label": "Fried Rice", "confidence": 0.91}],
        },
    )
    response = client.post(
        "/analyze",
        data={"image": (make_image(), "dinner.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert b"AI estimate" in response.data
    assert b"Fried rice" in response.data
    assert b"91% match" in response.data


def test_history_shows_saved_daily_totals(client):
    client.post(
        "/meals",
        data={"food_id": "chapati", "serving_grams": "100", "meal_type": "Lunch"},
    )
    response = client.get("/history")
    assert response.status_code == 200
    assert b"Chapati" in response.data
    assert b"297" in response.data
    assert b"100 g serving" in response.data


def test_serving_size_and_meal_type_are_validated(client):
    bad_size = client.post(
        "/meals",
        data={"food_id": "idli", "serving_grams": "-4", "meal_type": "Breakfast"},
    )
    assert bad_size.status_code == 400
    bad_type = client.post(
        "/meals",
        data={"food_id": "idli", "serving_grams": "100", "meal_type": "Brunch"},
    )
    assert bad_type.status_code == 400


def test_upload_rejects_non_image_content(client):
    response = client.post(
        "/analyze",
        data={"image": (BytesIO(b"not an image"), "food.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert b"not a valid image" in response.data


def test_invalid_history_date_is_rejected(client):
    response = client.get("/history?date=not-a-date")
    assert response.status_code == 400
    assert b"valid calendar date" in response.data


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}
