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
app.url_map.strict_slashes = False
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
    hr = input_data["Heart rate"]
    temp = input_data["Body temperature"]
    pain = input_data["Pain severity - 0-10 verbal numeric rating [Score] - Reported"]
    glucose = input_data["Glucose [Mass/volume] in Blood"]
    hemoglobin = input_data["Hemoglobin [Mass/volume] in Blood"]
    bmi = input_data["Body mass index (BMI) [Ratio]"]

    def severity_label(value, moderate_threshold, high_threshold):
        if value >= high_threshold:
            return "marked"
        if value >= moderate_threshold:
            return "moderate"
        return "mild"

    def add_section(section_title, section_notes):
        if not section_notes:
            return []
        return ["", f"{section_title}:"] + [f"- {note}" for note in section_notes]

    notes = []

    if prediction == 1:
        if probability >= 0.85:
            risk_heading = "High-acuity risk pattern detected"
            disposition = "Urgent clinical review is recommended."
        elif probability >= 0.65:
            risk_heading = "Elevated risk pattern detected"
            disposition = "Prompt reassessment and clinician review are recommended."
        else:
            risk_heading = "Borderline risk pattern detected"
            disposition = "Repeat observations and monitor for progression."

        doctor_notes = []
        nursing_notes = []
        lab_notes = []
        monitoring_notes = []

        if temp >= 39:
            doctor_notes.append(
                f"Temperature is markedly elevated at {temp:.1f} C; assess for sepsis, acute infection, or inflammatory source."
            )
            monitoring_notes.append("Repeat temperature and review antipyretic response within the local observation interval.")
        elif temp > 38:
            doctor_notes.append(
                f"Temperature is febrile at {temp:.1f} C; correlate with infection symptoms, cultures, and inflammatory markers if available."
            )
        elif temp < 36:
            doctor_notes.append(
                f"Temperature is low at {temp:.1f} C; consider hypothermia, exposure, endocrine causes, or severe infection depending on context."
            )

        if hr >= 130:
            nursing_notes.append(
                f"Heart rate is severely elevated at {hr:.0f} bpm; place on close observation and assess perfusion, rhythm, and hydration status."
            )
        elif hr > 100:
            nursing_notes.append(
                f"Tachycardia present at {hr:.0f} bpm; reassess after pain control, fluids, fever management, and rest."
            )
        elif hr < 50:
            nursing_notes.append(
                f"Bradycardia present at {hr:.0f} bpm; review symptoms, medications, rhythm, and hemodynamic stability."
            )

        if pain >= 8:
            nursing_notes.append(
                f"Severe pain score of {pain:.0f}/10; escalate analgesia review and reassess after intervention."
            )
        elif pain >= 5:
            nursing_notes.append(
                f"Moderate pain score of {pain:.0f}/10; provide pain intervention and repeat pain scoring."
            )

        if glucose >= 200:
            lab_notes.append(
                f"Glucose is markedly elevated at {glucose:.0f} mg/dL; evaluate for acute hyperglycemia and dehydration risk."
            )
        elif glucose > 126:
            lab_notes.append(
                f"Glucose is above expected range at {glucose:.0f} mg/dL; review diabetes history, fasting status, and recent intake."
            )
        elif glucose < 70:
            lab_notes.append(
                f"Glucose is low at {glucose:.0f} mg/dL; treat per hypoglycemia protocol and reassess."
            )

        if hemoglobin < 8:
            lab_notes.append(
                f"Hemoglobin is critically low at {hemoglobin:.1f} g/dL; assess bleeding, symptoms, and transfusion criteria."
            )
        elif hemoglobin < 12:
            lab_notes.append(
                f"Hemoglobin is reduced at {hemoglobin:.1f} g/dL; correlate with anemia symptoms, bleeding risk, and baseline values."
            )

        if bmi >= 30:
            monitoring_notes.append(
                f"BMI is {bmi:.1f}; consider weight-based dosing, mobility needs, and cardiometabolic risk during review."
            )
        elif bmi < 18.5:
            monitoring_notes.append(
                f"BMI is {bmi:.1f}; consider nutritional status, frailty, and medication dosing implications."
            )

        if not doctor_notes:
            doctor_notes.append("No dominant temperature-driven physician rule was triggered; interpret the model score with the full clinical picture.")
        if not nursing_notes:
            nursing_notes.append("No major heart-rate or pain escalation rule was triggered; continue routine observation frequency unless symptoms change.")
        if not lab_notes:
            lab_notes.append("Glucose and hemoglobin are not crossing the simple alert thresholds used by this rule layer.")

        notes.append(risk_heading)
        notes.append(f"Confidence: {probability * 100:.2f}%")
        notes.append(f"Overall pattern: {severity_label(probability, 0.65, 0.85).title()} model concern based on current observations.")
        notes.extend(add_section("Physician Review", doctor_notes))
        notes.extend(add_section("Nursing Priorities", nursing_notes))
        notes.extend(add_section("Laboratory Context", lab_notes))
        notes.extend(add_section("Monitoring Plan", monitoring_notes))
        notes.append("")
        notes.append(disposition)
    else:
        stable_confidence = 1 - probability
        stable_notes = []

        if hr > 100:
            stable_notes.append(f"Heart rate remains elevated at {hr:.0f} bpm; continue trend monitoring.")
        if temp > 38:
            stable_notes.append(f"Temperature is febrile at {temp:.1f} C; reassess if symptoms progress.")
        if pain >= 5:
            stable_notes.append(f"Pain score is {pain:.0f}/10; treat and document response.")
        if glucose > 126:
            stable_notes.append(f"Glucose is above expected range at {glucose:.0f} mg/dL; follow local glucose monitoring guidance.")
        if hemoglobin < 12:
            stable_notes.append(f"Hemoglobin is reduced at {hemoglobin:.1f} g/dL; compare with baseline if available.")
        if not stable_notes:
            stable_notes.append("Current observations do not cross the simple alert thresholds used by this rule layer.")

        notes.append("Lower-risk pattern at this time")
        notes.append(f"Confidence: {stable_confidence * 100:.2f}%")
        notes.extend(add_section("Continue Monitoring", stable_notes))
        notes.append("")
        notes.append("Continue routine monitoring and reassess if clinical status changes.")

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
