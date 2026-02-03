import csv
import json
import io
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from fastapi.responses import StreamingResponse
from database_mongo import MongoDB, PREDICTIONS_COLLECTION, ANALYTICS_COLLECTION
import logging

logger = logging.getLogger(__name__)

CSV_MEDIA_TYPE = "text/csv"
TOTAL_PREDICTIONS = "Total Predictions"
AVG_CONFIDENCE = "Avg Confidence"

async def export_predictions_csv(
    user_id: Optional[str] = None,
    emotion: Optional[str] = None,
    days: int = 30,
    include_features: bool = False
) -> StreamingResponse:
    """Export predictions data as CSV."""
    db = MongoDB.get_database()

    # Build query
    query = {"created_at": {"$gte": datetime.now(datetime.timezone.utc) - timedelta(days=days)}}
    if user_id:
        query["user_id"] = user_id
    if emotion:
        query["emotion"] = emotion

    # Get predictions
    predictions = await db[PREDICTIONS_COLLECTION].find(query)\
        .sort("created_at", -1)\
        .to_list(length=None)

    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    header = [
        "prediction_id", "user_id", "filename", "emotion", "confidence",
        "model_type", "model_version", "processing_time", "audio_duration",
        "spectrogram_id", "created_at"
    ]
    if include_features:
        header.append("features")

    writer.writerow(header)

    # Write data
    for pred in predictions:
        row = [
            str(pred.get("_id", "")),
            pred.get("user_id", ""),
            pred.get("filename", ""),
            pred.get("emotion", ""),
            pred.get("confidence", ""),
            pred.get("model_type", ""),
            pred.get("model_version", ""),
            pred.get("processing_time", ""),
            pred.get("audio_duration", ""),
            str(pred.get("spectrogram_id", "")) if pred.get("spectrogram_id") else "",
            pred.get("created_at", "").isoformat() if pred.get("created_at") else ""
        ]

        if include_features:
            features = pred.get("features", {})
            row.append(json.dumps(features))

        writer.writerow(row)

    output.seek(0)

    # Create streaming response
    def generate():
        yield output.getvalue()

    filename = f"predictions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        generate(),
        media_type=CSV_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

async def export_predictions_json(
    user_id: Optional[str] = None,
    emotion: Optional[str] = None,
    days: int = 30,
    include_features: bool = False
) -> StreamingResponse:
    """Export predictions data as JSON."""
    db = MongoDB.get_database()

    # Build query
    query = {"created_at": {"$gte": datetime.now(datetime.timezone.utc) - timedelta(days=days)}}
    if user_id:
        query["user_id"] = user_id
    if emotion:
        query["emotion"] = emotion

    # Get predictions
    predictions = await db[PREDICTIONS_COLLECTION].find(query)\
        .sort("created_at", -1)\
        .to_list(length=None)

    # Convert ObjectId to string and format data
    export_data = []
    for pred in predictions:
        prediction_data = {
            "prediction_id": str(pred["_id"]),
            "user_id": pred.get("user_id"),
            "filename": pred.get("filename"),
            "emotion": pred.get("emotion"),
            "confidence": pred.get("confidence"),
            "model_type": pred.get("model_type"),
            "model_version": pred.get("model_version"),
            "processing_time": pred.get("processing_time"),
            "audio_duration": pred.get("audio_duration"),
            "spectrogram_id": str(pred["spectrogram_id"]) if pred.get("spectrogram_id") else None,
            "created_at": pred.get("created_at").isoformat() if pred.get("created_at") else None
        }

        if include_features:
            prediction_data["features"] = pred.get("features", {})

        export_data.append(prediction_data)

    # Create JSON content
    json_data = {
        "export_info": {
            "timestamp": datetime.now(datetime.timezone.utc).isoformat(),
            "total_records": len(export_data),
            "filters": {
                "user_id": user_id,
                "emotion": emotion,
                "days": days
            }
        },
        "predictions": export_data
    }

    json_output = json.dumps(json_data, indent=2, default=str)

    def generate():
        yield json_output

    filename = f"predictions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

async def export_analytics_csv(days: int = 30) -> StreamingResponse:
    """Export analytics data as CSV."""
    from services.analytics_service import get_ml_model_performance, get_system_analytics

    # Get analytics data
    model_performance = await get_ml_model_performance(days)
    system_analytics = await get_system_analytics(days)

    output = io.StringIO()
    writer = csv.writer(output)

    # Write model performance section
    writer.writerow(["MODEL PERFORMANCE ANALYTICS"])
    writer.writerow([])
    writer.writerow(["Model Version", TOTAL_PREDICTIONS, AVG_CONFIDENCE, "Avg Processing Time",
                    "High Confidence Ratio", "Low Confidence Ratio", "Performance Score"])

    for model_version, metrics in model_performance["model_performance"].items():
        writer.writerow([
            model_version,
            metrics["total_predictions"],
            f"{metrics['avg_confidence']:.3f}",
            f"{metrics['avg_processing_time']:.3f}",
            f"{metrics['high_confidence_ratio']:.3f}",
            f"{metrics['low_confidence_ratio']:.3f}",
            f"{metrics['performance_score']:.3f}"
        ])

    writer.writerow([])
    writer.writerow(["DAILY TRENDS"])
    writer.writerow([])
    writer.writerow(["Date", "Predictions", AVG_CONFIDENCE, "Avg Processing Time", "High Confidence Ratio"])

    for date, trends in model_performance["daily_trends"].items():
        writer.writerow([
            date,
            trends["predictions"],
            f"{trends['avg_confidence']:.3f}",
            f"{trends['avg_processing_time']:.3f}",
            f"{trends['high_confidence_ratio']:.3f}"
        ])

    writer.writerow([])
    writer.writerow(["SYSTEM ANALYTICS"])
    writer.writerow([])
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Period Days", system_analytics["period_days"]])
    writer.writerow(["Total Predictions", system_analytics["total_predictions"]])
    writer.writerow(["Active Users", system_analytics["active_users"]])

    writer.writerow([])
    writer.writerow(["Emotion Distribution"])
    for emotion, count in system_analytics["emotion_distribution"].items():
        writer.writerow([emotion, count])

    writer.writerow([])
    writer.writerow(["Daily Activity"])
    for date, predictions in system_analytics["daily_activity"].items():
        writer.writerow([date, predictions])

    output.seek(0)

    def generate():
        yield output.getvalue()

    filename = f"analytics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        generate(),
        media_type=CSV_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

async def export_user_insights_csv(user_id: str) -> StreamingResponse:
    """Export user insights as CSV."""
    from services.analytics_service import get_user_insights

    insights = await get_user_insights(user_id)

    output = io.StringIO()
    writer = csv.writer(output)

    # Write user summary
    writer.writerow(["USER INSIGHTS REPORT"])
    writer.writerow([])
    writer.writerow(["User ID", insights["user_id"]])
    writer.writerow([TOTAL_PREDICTIONS, insights["total_predictions"]])
    writer.writerow(["Average Confidence", f"{insights['avg_confidence']:.3f}"])
    writer.writerow(["Most Common Emotion", insights["most_common_emotion"] or "N/A"])
    writer.writerow(["Prediction Streak", insights["prediction_streak"]])

    if insights.get("first_prediction"):
        writer.writerow(["First Prediction", insights["first_prediction"].isoformat()])
    if insights.get("last_prediction"):
        writer.writerow(["Last Prediction", insights["last_prediction"].isoformat()])

    writer.writerow([])
    writer.writerow(["WEEKLY ACTIVITY"])
    writer.writerow([])
    writer.writerow(["Date", "Predictions", AVG_CONFIDENCE])

    for date, activity in insights["weekly_activity"].items():
        writer.writerow([
            date,
            activity["predictions"],
            f"{activity['avg_confidence']:.3f}"
        ])

    writer.writerow([])
    writer.writerow(["EMOTION DISTRIBUTION"])
    writer.writerow([])
    writer.writerow(["Emotion", "Count"])

    for emotion, count in insights["emotion_distribution"].items():
        writer.writerow([emotion, count])

    output.seek(0)

    def generate():
        yield output.getvalue()

    filename = f"user_insights_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        generate(),
        media_type=CSV_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
