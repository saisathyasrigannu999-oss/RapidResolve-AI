from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///rapidresolve.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))
    location = db.Column(db.String(100))
    priority = db.Column(db.String(20))
    department = db.Column(db.String(50))
    status = db.Column(db.String(30), default="Pending")
    report_count = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def analyze_report(description):
    text = description.lower()

    category = "Other"
    department = "Administration"
    priority = "Low"
    reason = "General campus issue detected."
    recommendation = "Forward the issue to campus administration."
    confidence = 70

    if any(word in text for word in [
        "fire", "smoke", "shock", "danger",
        "accident", "injury", "unsafe"
    ]):
        category = "Safety"
        department = "Security"
        priority = "Critical"
        reason = "The report indicates a potential safety or emergency risk."
        recommendation = "Immediately alert campus security and emergency response staff."
        confidence = 96

    elif any(word in text for word in [
        "electricity", "power", "current",
        "light", "fan", "spark"
    ]):
        category = "Electricity"
        department = "Electrical"
        priority = "High"
        reason = "Electrical failure may affect campus operations or safety."
        recommendation = "Notify the electrical maintenance team immediately."
        confidence = 94

    elif any(word in text for word in [
        "water", "tap", "washroom",
        "bathroom", "water supply"
    ]):
        category = "Water Supply"
        department = "Maintenance"
        priority = "High"
        reason = "Water availability affects essential campus facilities."
        recommendation = "Notify the maintenance department and inspect the water supply."
        confidence = 95

    elif any(word in text for word in [
        "wifi", "wi-fi", "internet",
        "network", "connection"
    ]):
        category = "Wi-Fi"
        department = "IT"
        priority = "Medium"
        reason = "Network connectivity is affecting digital campus services."
        recommendation = "Forward the issue to the IT/network support team."
        confidence = 93

    elif any(word in text for word in [
        "garbage", "dust", "dirty",
        "clean", "waste", "smell"
    ]):
        category = "Cleanliness"
        department = "Sanitation"
        priority = "Medium"
        reason = "The report indicates a sanitation or cleanliness issue."
        recommendation = "Assign the issue to the sanitation team for inspection."
        confidence = 92

    elif any(word in text for word in [
        "bus", "transport", "driver"
    ]):
        category = "Transport"
        department = "Transport"
        priority = "Medium"
        reason = "The report is related to campus transportation."
        recommendation = "Forward the incident to the transport department."
        confidence = 91

    elif any(word in text for word in [
        "bench", "desk", "chair",
        "projector", "computer", "lab"
    ]):
        category = "Classroom / Equipment"
        department = "Maintenance"
        priority = "Medium"
        reason = "The report indicates damaged or malfunctioning campus equipment."
        recommendation = "Assign the issue to the maintenance team."
        confidence = 90

    return category, department, priority, reason, recommendation, confidence
    text = description.lower()

    category = "Other"
    department = "Administration"
    priority = "Low"

    if any(word in text for word in ["fire", "smoke", "shock", "danger", "accident"]):
        category = "Safety"
        department = "Security"
        priority = "Critical"

    elif any(word in text for word in ["electricity", "power", "current", "light", "fan"]):
        category = "Electricity"
        department = "Electrical"
        priority = "High"

    elif any(word in text for word in ["water", "tap", "washroom", "bathroom"]):
        category = "Water Supply"
        department = "Maintenance"
        priority = "High"

    elif any(word in text for word in ["wifi", "wi-fi", "internet", "network"]):
        category = "Wi-Fi"
        department = "IT"
        priority = "Medium"

    elif any(word in text for word in ["garbage", "dust", "dirty", "clean", "waste", "smell"]):
        category = "Cleanliness"
        department = "Sanitation"
        priority = "Medium"

    elif any(word in text for word in ["bus", "transport"]):
        category = "Transport"
        department = "Transport"
        priority = "Medium"

    elif any(word in text for word in ["bench", "desk", "chair", "projector", "lab"]):
        category = "Classroom / Equipment"
        department = "Maintenance"
        priority = "Medium"

    return category, department, priority


def find_duplicate(category, location):
    incidents = Incident.query.filter_by(category=category, location=location).all()

    for incident in incidents:
        if incident.status != "Resolved":
            return incident

    return None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/report", methods=["POST"])
def report():
    description = request.form["description"]
    location = request.form["location"]
    image = request.files.get("image")
    image_filename = None

    if image and image.filename:
        image_filename = secure_filename(image.filename)
        image.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                image_filename
            )
        )

    category, department, priority, reason, recommendation, confidence = analyze_report(description)

    duplicate = find_duplicate(category, location)

    if duplicate:
        duplicate.report_count += 1

        if duplicate.report_count >= 3 and priority == "Medium":
            duplicate.priority = "High"

        db.session.commit()

        return render_template(
    "result.html",
    incident=duplicate,
    duplicate=True,
    reason=reason,
    recommendation=recommendation,
    confidence=confidence
)

    incident = Incident(
        description=description,
        category=category,
        location=location,
        priority=priority,
        department=department
    )

    db.session.add(incident)
    db.session.commit()

    return render_template(
    "result.html",
    incident=incident,
    duplicate=False,
    reason=reason,
    recommendation=recommendation,
    confidence=confidence
)

@app.route("/admin")
def admin():

    incidents = Incident.query.order_by(
        Incident.created_at.desc()
    ).all()

    total = Incident.query.count()

    critical = Incident.query.filter_by(
        priority="Critical"
    ).count()

    high = Incident.query.filter_by(
        priority="High"
    ).count()

    medium = Incident.query.filter_by(
        priority="Medium"
    ).count()

    low = Incident.query.filter_by(
        priority="Low"
    ).count()

    crisis_alerts = []

    for incident in incidents:
        if incident.report_count >= 3:
            crisis_alerts.append(incident)

    categories = {}

    for incident in incidents:
        categories[incident.category] = categories.get(
            incident.category, 0
        ) + incident.report_count

    return render_template(
        "admin.html",
        incidents=incidents,
        total=total,
        critical=critical,
        high=high,
        medium=medium,
        low=low,
        crisis_alerts=crisis_alerts,
        categories=categories
    )
@app.route("/update/<int:incident_id>/<status>")
def update_status(incident_id, status):
    incident = Incident.query.get_or_404(incident_id)
    incident.status = status
    db.session.commit()

    return redirect(url_for("admin"))


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)