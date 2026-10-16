import logging
import math
import re
import uuid
from datetime import date
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from PIL import Image, UnidentifiedImageError
from requests.exceptions import RequestException

from .database import (
    get_db,
    get_food,
    get_foods,
    get_meal_rows,
    get_weekly_calories,
    summarize_meals,
)
from .nutrition import SOURCES
from .recognition import recognize_food

logger = logging.getLogger(__name__)
bp = Blueprint("main", __name__)
IMAGE_FILENAME = re.compile(r"^[0-9a-f]{32}\.jpg$")
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_IMAGE_PIXELS = 20_000_000
MEAL_TYPES = ("Breakfast", "Lunch", "Dinner", "Snack")
RECOGNITION_ERRORS = (
    ImportError,
    OSError,
    RequestException,
    RuntimeError,
    ValueError,
)


def _image_directory():
    return Path(current_app.config["UPLOAD_FOLDER"])


def _valid_saved_image(filename):
    return bool(IMAGE_FILENAME.fullmatch(filename or "")) and (
        _image_directory() / filename
    ).is_file()


def _dashboard_context(result=None, error=None, image_filename="", candidates=None):
    connection = get_db()
    today = date.today().isoformat()
    meals = get_meal_rows(connection, today)
    return {
        "foods": get_foods(connection),
        "result": result,
        "error": error,
        "image_filename": image_filename,
        "candidates": candidates or [],
        "meals": meals,
        "totals": summarize_meals(meals),
        "weekly": get_weekly_calories(connection),
        "today": today,
        "meal_types": MEAL_TYPES,
        "sources": SOURCES,
    }


def _render_dashboard(result=None, error=None, image_filename="", candidates=None):
    return render_template(
        "index.html",
        **_dashboard_context(result, error, image_filename, candidates),
    )


def _save_uploaded_image(upload):
    try:
        with Image.open(upload.stream) as image:
            if image.format not in ALLOWED_IMAGE_FORMATS:
                return None, "Please upload a JPEG, PNG, or WebP food image."
            if image.width * image.height > MAX_IMAGE_PIXELS:
                return None, "That image has too many pixels to process. Please upload a smaller image."
            image.verify()
        upload.stream.seek(0)
        with Image.open(upload.stream) as image:
            normalized = image.convert("RGB")
            filename = f"{uuid.uuid4().hex}.jpg"
            normalized.save(_image_directory() / filename, format="JPEG", quality=88)
        return filename, None
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
        return None, "That file is not a valid image. Please choose a JPEG, PNG, or WebP."


@bp.get("/")
def index():
    return _render_dashboard()


@bp.post("/analyze")
def analyze():
    food_id = request.form.get("food_id", "").strip()
    manual_food = get_food(food_id) if food_id else None
    if food_id and manual_food is None:
        return _render_dashboard(error="Please choose a food from the list."), 400

    upload = request.files.get("image")
    image_filename = request.form.get("image_filename", "").strip()

    if upload and upload.filename:
        image_filename, upload_error = _save_uploaded_image(upload)
        if upload_error:
            return _render_dashboard(error=upload_error), 400
    elif image_filename and not _valid_saved_image(image_filename):
        return _render_dashboard(
            error="The selected image is no longer available. Please upload it again."
        ), 400

    if food_id:
        return _render_dashboard(
            result={
                "food": manual_food,
                "confidence": None,
                "method": "manual",
                "image_filename": image_filename,
            },
            image_filename=image_filename,
        )

    if not image_filename:
        return _render_dashboard(
            error="Upload a food image or choose a food for manual estimation."
        ), 400

    try:
        with Image.open(_image_directory() / image_filename) as image:
            image.load()
            prepared_image = image.convert("RGB")
    except (UnidentifiedImageError, OSError):
        logger.exception("A saved food image could not be opened.")
        return _render_dashboard(
            error="The uploaded image could not be read. Please upload it again."
        ), 400

    try:
        prediction = recognize_food(prepared_image)
    except RECOGNITION_ERRORS:
        logger.exception("Food recognition could not complete.")
        return _render_dashboard(
            error=(
                "The AI model could not be loaded or run. Check your internet "
                "connection and installed dependencies, or choose a food below "
                "for a manual estimate. Your image is ready for a second try."
            ),
            image_filename=image_filename,
        )

    if prediction["status"] != "identified":
        return _render_dashboard(
            error=(
                "We couldn't confidently match this image to a food in the "
                "recognition catalog. No food or nutrition was guessed. Choose "
                "the food manually below to get an estimate."
            ),
            image_filename=image_filename,
            candidates=prediction["candidates"],
        )

    food = get_food(prediction["food_id"])
    if food is None:
        logger.error("Model returned food id missing from nutrition database.")
        return _render_dashboard(
            error="The recognized food has no nutrition entry. Choose another food manually.",
            image_filename=image_filename,
        )
    return _render_dashboard(
        result={
            "food": food,
            "confidence": prediction["confidence"],
            "method": "ai",
            "image_filename": image_filename,
            "candidates": prediction["candidates"],
        },
        image_filename=image_filename,
    )


@bp.post("/meals")
def save_meal():
    food_id = request.form.get("food_id", "").strip()
    meal_type = request.form.get("meal_type", "").strip()
    image_filename = request.form.get("image_filename", "").strip() or None

    food = get_food(food_id)
    if food is None:
        abort(400, description="Choose a valid food before saving.")

    try:
        serving_grams = float(request.form.get("serving_grams", ""))
    except ValueError:
        abort(400, description="Enter a valid serving size in grams.")
    if not math.isfinite(serving_grams) or not 1 <= serving_grams <= 5000:
        abort(400, description="Serving size must be between 1 g and 5000 g.")
    if meal_type not in MEAL_TYPES:
        abort(400, description="Choose a valid meal type.")
    if image_filename and not _valid_saved_image(image_filename):
        abort(400, description="The selected image is no longer available.")

    connection = get_db()
    connection.execute(
        """
        INSERT INTO meals (food_id, serving_grams, meal_type, eaten_on, image_filename)
        VALUES (?, ?, ?, ?, ?)
        """,
        (food_id, serving_grams, meal_type, date.today().isoformat(), image_filename),
    )
    connection.commit()
    return redirect(url_for("main.index"), code=303)


@bp.get("/history")
def history():
    raw_date = request.args.get("date", date.today().isoformat())
    try:
        selected_date = date.fromisoformat(raw_date)
    except ValueError:
        return render_template(
            "error.html",
            message="Choose a valid calendar date to view meal history.",
        ), 400

    meals = get_meal_rows(get_db(), selected_date.isoformat())
    return render_template(
        "history.html",
        foods=get_foods(),
        meals=meals,
        totals=summarize_meals(meals),
        selected_date=selected_date.isoformat(),
        display_date=(
            selected_date.strftime("%A, %B ")
            + str(selected_date.day)
            + selected_date.strftime(", %Y")
        ),
        meal_types=MEAL_TYPES,
    )


@bp.get("/meal-image/<filename>")
def meal_image(filename):
    if not _valid_saved_image(filename):
        abort(404)
    return send_from_directory(_image_directory(), filename, max_age=3600)
