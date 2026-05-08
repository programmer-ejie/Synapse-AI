import os
from pathlib import Path

import joblib
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR
MODEL_PATH = MODEL_DIR / "risk_model_v3_clinical.pkl"
FEATURES_PATH = MODEL_DIR / "risk_model_v3_features.pkl"

app = Flask(__name__)
CORS(app)

model = joblib.load(MODEL_PATH)
features = joblib.load(FEATURES_PATH)


def _to_float(value, field_name):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a number.")


def build_model_input(payload):
    missing = [feature for feature in features if feature not in payload]
    if missing:
        raise ValueError(f"Missing required feature(s): {', '.join(missing)}")

    row = {feature: _to_float(payload[feature], feature) for feature in features}
    return pd.DataFrame([row], columns=features)


def generate_recommendation(input_data, prediction, probability):
    notes = []

    hr = input_data["Heart rate"]
    temp = input_data["Body temperature"]
    pain = input_data["Pain severity - 0-10 verbal numeric rating [Score] - Reported"]
    glucose = input_data["Glucose [Mass/volume] in Blood"]
    hemoglobin = input_data["Hemoglobin [Mass/volume] in Blood"]

    if prediction == 1:
        notes.append("HIGH RISK DETECTED (Multi-Role Assessment)")
        notes.append(f"Confidence: {probability * 100:.2f}%")
        notes.append("")
        notes.append("Doctor Assessment:")
        if temp > 38:
            notes.append("- Possible infection or inflammatory response.")
        if glucose > 126:
            notes.append("- Elevated glucose level (possible hyperglycemia).")
        if hemoglobin < 12:
            notes.append("- Low hemoglobin (possible anemia).")
        if temp <= 38 and glucose <= 126 and hemoglobin >= 12:
            notes.append("- No major doctor-facing rule indicators were triggered.")

        notes.append("")
        notes.append("Nursing Observations:")
        if hr > 100:
            notes.append("- Tachycardia observed.")
        if pain >= 5:
            notes.append("- Patient experiencing moderate to high pain.")
        if hr <= 100 and pain < 5:
            notes.append("- No major nursing rule indicators were triggered.")

        notes.append("")
        notes.append("Lab Indicators:")
        if glucose > 126:
            notes.append("- Blood glucose above normal range.")
        if hemoglobin < 12:
            notes.append("- Hemoglobin below normal range.")
        if glucose <= 126 and hemoglobin >= 12:
            notes.append("- Lab values are within the simple rule thresholds.")

        notes.append("")
        notes.append("Immediate clinical evaluation recommended.")
    else:
        stable_confidence = 1 - probability
        notes.append("Patient Stable")
        notes.append(f"Confidence: {stable_confidence * 100:.2f}%")
        notes.append("Continue monitoring.")

    return "\n".join(notes)


@app.get("/")
def index():
    return jsonify(
        {
            "service": "Synapse AI risk_model_v3 API",
            "status": "running",
            "endpoints": {
                "health": "GET /health",
                "features": "GET /features",
                "predict": "POST /predict",
            },
        }
    )


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "model_loaded": model is not None,
            "feature_count": len(features),
        }
    )


@app.get("/features")
def get_features():
    return jsonify({"features": features})


@app.post("/predict")
def predict():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    try:
        model_input = build_model_input(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc), "required_features": features}), 400

    prediction = int(model.predict(model_input)[0])
    probabilities = model.predict_proba(model_input)[0]
    risk_probability = float(probabilities[1])
    input_data = model_input.iloc[0].to_dict()
    recommendation = generate_recommendation(input_data, prediction, risk_probability)

    return jsonify(
        {
            "model": "risk_model_v3_clinical",
            "prediction": prediction,
            "risk_label": "High Risk" if prediction == 1 else "Normal",
            "risk_probability": risk_probability,
            "confidence_percent": round(risk_probability * 100, 2)
            if prediction == 1
            else round((1 - risk_probability) * 100, 2),
            "recommendation": recommendation,
            "input_features": input_data,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
