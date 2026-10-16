from threading import Lock

from .nutrition import FOOD101_TO_FOOD_ID

MODEL_ID = "nateraw/food"
MIN_CONFIDENCE = 0.20
_classifier = None
_classifier_lock = Lock()


def _load_classifier():
    global _classifier
    if _classifier is None:
        with _classifier_lock:
            if _classifier is None:
                from transformers import pipeline

                _classifier = pipeline(
                    "image-classification",
                    model=MODEL_ID,
                    device=-1,
                )
    return _classifier


def recognize_food(image):
    """Return a supported food id and confidence, or an explicit non-match."""
    predictions = _load_classifier()(image, top_k=3)

    if not predictions:
        return {"status": "unrecognized", "candidates": []}

    candidates = [
        {
            "label": str(item["label"]).replace("_", " ").title(),
            "confidence": round(float(item["score"]), 3),
        }
        for item in predictions
    ]
    top_prediction = predictions[0]
    label = str(top_prediction["label"]).strip().lower().replace(" ", "_")
    confidence = float(top_prediction["score"])
    food_id = FOOD101_TO_FOOD_ID.get(label)
    if confidence < MIN_CONFIDENCE or food_id is None:
        return {
            "status": "unrecognized",
            "candidates": candidates,
        }
    return {
        "status": "identified",
        "food_id": food_id,
        "confidence": confidence,
        "candidates": candidates,
    }
