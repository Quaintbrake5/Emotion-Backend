from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from database_mongo import MongoDB, PREDICTIONS_COLLECTION, ANALYTICS_COLLECTION
import logging

logger = logging.getLogger(__name__)

# Constants for chart configuration
CHART_TYPE_LINE = "line"
TITLE_PREDICTION_TRENDS = "Prediction Trends Over Time"
LABEL_PREDICTIONS = "Predictions"
LABEL_AVG_CONFIDENCE = "Avg Confidence"
BORDER_COLOR_PREDICTIONS = "rgb(75, 192, 192)"
BACKGROUND_COLOR_PREDICTIONS = "rgba(75, 192, 192, 0.2)"
BORDER_COLOR_CONFIDENCE = "rgb(255, 99, 132)"
BACKGROUND_COLOR_CONFIDENCE = "rgba(255, 99, 132, 0.2)"
Y_AXIS_ID_Y = "y"
Y_AXIS_ID_Y1 = "y1"
TEXT_NUM_PREDICTIONS = "Number of Predictions"
TEXT_CONFIDENCE_SCORE = "Confidence Score"
AXIS_TYPE_LINEAR = "linear"
AXIS_POSITION_LEFT = "left"
AXIS_POSITION_RIGHT = "right"

# MongoDB aggregation pipeline operators
PIPELINE_MATCH = "$match"
PIPELINE_GROUP = "$group"
PIPELINE_SORT = "$sort"
PIPELINE_PROJECT = "$project"
PIPELINE_DATE = "$dateToString"
PIPELINE_HOUR = "$hour"
PIPELINE_SUM = "$sum"
PIPELINE_AVG = "$avg"
PIPELINE_MIN = "$min"
PIPELINE_MAX = "$max"
PIPELINE_ADD_TO_SET = "$addToSet"
PIPELINE_PUSH = "$push"
PIPELINE_ROUND = "$round"
PIPELINE_DIVIDE = "$divide"
PIPELINE_COND = "$cond"
PIPELINE_GTE = "$gte"

# Field references
CREATED_AT = "$created_at"
CONFIDENCE = "$confidence"
EMOTION = "$emotion"
MODEL_VERSION = "$model_version"
PROCESSING_TIME = "$processing_time"
USER_ID = "$user_id"


async def get_user_prediction_trends(
    user_id: str,
    days: int = 30
) -> Dict[str, Any]:
    """Get user's prediction trends for time-series visualization."""
    db = MongoDB.get_database()

    # Aggregate predictions by date
    pipeline = [
        {
            PIPELINE_MATCH: {
                "user_id": user_id,
                CREATED_AT: {PIPELINE_GTE: datetime.now(datetime.timezone.utc) - timedelta(days=days)}
            }
        },
        {
            PIPELINE_GROUP: {
                "_id": {
                    PIPELINE_DATE: {
                        "format": "%Y-%m-%d",
                        "date": CREATED_AT
                    }
                },
                "predictions": {PIPELINE_SUM: 1},
                "avg_confidence": {PIPELINE_AVG: CONFIDENCE},
                "emotions": {PIPELINE_PUSH: EMOTION}
            }
        },
        {
            PIPELINE_SORT: {"_id": 1}
        }
    ]

    results = await db[PREDICTIONS_COLLECTION].aggregate(pipeline).to_list(length=None)

    # Process results for frontend
    dates = []
    prediction_counts = []
    confidence_scores = []
    emotion_distribution = {}

    for result in results:
        dates.append(result["_id"])
        prediction_counts.append(result["predictions"])
        confidence_scores.append(round(result["avg_confidence"], 3) if result["avg_confidence"] else 0)

        # Count emotions for each day
        for emotion in result["emotions"]:
            emotion_distribution[emotion] = emotion_distribution.get(emotion, 0) + 1

    return {
        "chart_type": CHART_TYPE_LINE,
        "title": TITLE_PREDICTION_TRENDS,
        "data": {
            "labels": dates,
            "datasets": [
                {
                    "label": LABEL_PREDICTIONS,
                    "data": prediction_counts,
                    "borderColor": BORDER_COLOR_PREDICTIONS,
                    "backgroundColor": BACKGROUND_COLOR_PREDICTIONS,
                    "yAxisID": Y_AXIS_ID_Y
                },
                {
                    "label": LABEL_AVG_CONFIDENCE,
                    "data": confidence_scores,
                    "borderColor": BORDER_COLOR_CONFIDENCE,
                    "backgroundColor": BACKGROUND_COLOR_CONFIDENCE,
                    "yAxisID": Y_AXIS_ID_Y1
                }
            ]
        },
        "options": {
            "scales": {
                "y": {
                    "type": AXIS_TYPE_LINEAR,
                    "display": True,
                    "position": AXIS_POSITION_LEFT,
                    "title": {
                        "display": True,
                        "text": TEXT_NUM_PREDICTIONS
                    }
                },
                "y1": {
                    "type": AXIS_TYPE_LINEAR,
                    "display": True,
                    "position": AXIS_POSITION_RIGHT,
                    "title": {
                        "display": True,
                        "text": TEXT_CONFIDENCE_SCORE
                    },
                    "min": 0,
                    "max": 1
                }
            }
        }
    }

async def get_emotion_distribution(user_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
    """Get emotion distribution for pie/bar chart."""
    db = MongoDB.get_database()

    # Build match query
    match_query = {CREATED_AT: {PIPELINE_GTE: datetime.now(datetime.timezone.utc) - timedelta(days=days)}}
    if user_id:
        match_query["user_id"] = user_id

    pipeline = [
        {PIPELINE_MATCH: match_query},
        {
            PIPELINE_GROUP: {
                "_id": EMOTION,
                "count": {PIPELINE_SUM: 1},
                "avg_confidence": {PIPELINE_AVG: CONFIDENCE}
            }
        },
        {PIPELINE_SORT: {"count": -1}}
    ]

    results = await db[PREDICTIONS_COLLECTION].aggregate(pipeline).to_list(length=None)

    emotions = []
    counts = []
    confidences = []
    colors = [
        "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF",
        "#FF9F40", "#FF6384", "#C9CBCF", "#4BC0C0", "#FF6384"
    ]

    for i, result in enumerate(results):
        emotions.append(result["_id"])
        counts.append(result["count"])
        confidences.append(round(result["avg_confidence"], 3) if result["avg_confidence"] else 0)

    return {
        "chart_type": "doughnut",
        "title": "Emotion Distribution",
        "data": {
            "labels": emotions,
            "datasets": [{
                "data": counts,
                "backgroundColor": colors[:len(emotions)],
                "hoverBackgroundColor": colors[:len(emotions)]
            }]
        },
        "options": {
            "responsive": True,
            "plugins": {
                "legend": {
                    "position": "right"
                },
                "tooltip": {
                    "callbacks": {
                        "label": "function(context) { return context.label + ': ' + context.parsed + ' predictions'; }"
                    }
                }
            }
        },
        "emotion_confidence": dict(zip(emotions, confidences))
    }

async def get_model_performance_comparison(days: int = 30) -> Dict[str, Any]:
    """Get model performance comparison for bar chart."""
    db = MongoDB.get_database()

    pipeline = [
        {
            PIPELINE_MATCH: {
                CREATED_AT: {PIPELINE_GTE: datetime.now(datetime.timezone.utc) - timedelta(days=days)}
            }
        },
        {
            PIPELINE_GROUP: {
                "_id": MODEL_VERSION,
                "total_predictions": {PIPELINE_SUM: 1},
                "avg_confidence": {PIPELINE_AVG: CONFIDENCE},
                "avg_processing_time": {PIPELINE_AVG: PROCESSING_TIME},
                "high_confidence_count": {
                    PIPELINE_SUM: {PIPELINE_COND: [{PIPELINE_GTE: [CONFIDENCE, 0.8]}, 1, 0]}
                }
            }
        },
        {
            PIPELINE_PROJECT: {
                "model_version": "$_id",
                "total_predictions": 1,
                "avg_confidence": {PIPELINE_ROUND: ["$avg_confidence", 3]},
                "avg_processing_time": {PIPELINE_ROUND: ["$avg_processing_time", 3]},
                "high_confidence_ratio": {
                    PIPELINE_ROUND: [{PIPELINE_DIVIDE: ["$high_confidence_count", "$total_predictions"]}, 3]
                }
            }
        },
        {PIPELINE_SORT: {"avg_confidence": -1}}
    ]

    results = await db[PREDICTIONS_COLLECTION].aggregate(pipeline).to_list(length=None)

    model_versions = []
    confidences = []
    processing_times = []
    high_conf_ratios = []

    for result in results:
        model_versions.append(result["model_version"] or "Unknown")
        confidences.append(result["avg_confidence"] or 0)
        processing_times.append(result["avg_processing_time"] or 0)
        high_conf_ratios.append(result["high_confidence_ratio"] or 0)

    return {
        "chart_type": "bar",
        "title": "Model Performance Comparison",
        "data": {
            "labels": model_versions,
            "datasets": [
                {
                    "label": "Average Confidence",
                    "data": confidences,
                    "backgroundColor": "rgba(54, 162, 235, 0.8)",
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "borderWidth": 1
                },
                {
                    "label": "High Confidence Ratio (>0.8)",
                    "data": high_conf_ratios,
                    "backgroundColor": "rgba(75, 192, 192, 0.8)",
                    "borderColor": "rgba(75, 192, 192, 1)",
                    "borderWidth": 1
                }
            ]
        },
        "options": {
            "scales": {
                "y": {
                    "beginAtZero": True,
                    "max": 1
                }
            },
            "plugins": {
                "legend": {
                    "position": "top"
                }
            }
        },
        "processing_times": dict(zip(model_versions, processing_times))
    }

async def get_daily_activity_heatmap(days: int = 30) -> Dict[str, Any]:
    """Get daily activity heatmap data."""
    db = MongoDB.get_database()

    pipeline = [
        {
            PIPELINE_MATCH: {
                CREATED_AT: {PIPELINE_GTE: datetime.now(datetime.timezone.utc) - timedelta(days=days)}
            }
        },
        {
            PIPELINE_GROUP: {
                "_id": {
                    "date": {
                        PIPELINE_DATE: {
                            "format": "%Y-%m-%d",
                            "date": CREATED_AT
                        }
                    },
                    "hour": {
                        PIPELINE_HOUR: CREATED_AT
                    }
                },
                "count": {PIPELINE_SUM: 1}
            }
        },
        {
            PIPELINE_SORT: {"_id.date": 1, "_id.hour": 1}
        }
    ]

    results = await db[PREDICTIONS_COLLECTION].aggregate(pipeline).to_list(length=None)

    # Create heatmap data structure
    heatmap_data = []
    hours = list(range(24))
    dates = sorted({r["_id"]["date"] for r in results})

    for date in dates:
        day_data = [0] * 24
        for result in results:
            if result["_id"]["date"] == date:
                hour = result["_id"]["hour"]
                day_data[hour] = result["count"]
        heatmap_data.append(day_data)

    return {
        "chart_type": "heatmap",
        "title": "Daily Activity Heatmap",
        "data": {
            "dates": dates,
            "hours": hours,
            "values": heatmap_data
        },
        "options": {
            "xAxis": {
                "type": "category",
                "data": [f"{h}:00" for h in hours]
            },
            "yAxis": {
                "type": "category",
                "data": dates
            },
            "visualMap": {
                "min": 0,
                "max": max(max(row) for row in heatmap_data) if heatmap_data else 0,
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "bottom": "15%"
            },
            "series": [{
                "name": "Predictions",
                "type": "heatmap",
                "data": [
                    [i, j, heatmap_data[i][j]]
                    for i in range(len(dates))
                    for j in range(24)
                ],
                "label": {
                    "show": False
                },
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                }
            }]
        }
    }

async def get_user_engagement_metrics(user_id: str) -> Dict[str, Any]:
    """Get comprehensive user engagement metrics."""
    db = MongoDB.get_database()

    # Get user's prediction stats
    pipeline = [
        {PIPELINE_MATCH: {"user_id": user_id}},
        {
            PIPELINE_GROUP: {
                "_id": None,
                "total_predictions": {PIPELINE_SUM: 1},
                "avg_confidence": {PIPELINE_AVG: CONFIDENCE},
                "first_prediction": {PIPELINE_MIN: CREATED_AT},
                "last_prediction": {PIPELINE_MAX: CREATED_AT},
                "unique_emotions": {PIPELINE_ADD_TO_SET: EMOTION},
                "emotions": {PIPELINE_PUSH: EMOTION}
            }
        }
    ]

    user_stats = await db[PREDICTIONS_COLLECTION].aggregate(pipeline).to_list(length=1)

    if not user_stats:
        return {
            "total_predictions": 0,
            "avg_confidence": 0,
            "unique_emotions": 0,
            "most_common_emotion": None,
            "prediction_streak": 0,
            "engagement_score": 0
        }

    stats = user_stats[0]

    # Calculate most common emotion
    emotion_counts = {}
    for emotion in stats["emotions"]:
        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

    most_common_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else None

    # Calculate prediction streak (consecutive days)
    streak_pipeline = [
        {PIPELINE_MATCH: {"user_id": user_id}},
        {
            PIPELINE_GROUP: {
                "_id": {
                    PIPELINE_DATE: {
                        "format": "%Y-%m-%d",
                        "date": CREATED_AT
                    }
                },
                "count": {PIPELINE_SUM: 1}
            }
        },
        {PIPELINE_SORT: {"_id": -1}}
    ]

    daily_predictions = await db[PREDICTIONS_COLLECTION].aggregate(streak_pipeline).to_list(length=None)

    # Calculate streak
    streak = 0
    current_date = datetime.now(datetime.timezone.utc).date()

    for day_data in daily_predictions:
        day = datetime.strptime(day_data["_id"], "%Y-%m-%d").date()
        if day == current_date:
            streak += 1
            current_date -= timedelta(days=1)
        elif day == current_date - timedelta(days=1):
            streak += 1
            current_date = day
        else:
            break

    # Calculate engagement score (0-100)
    engagement_score = min(100, (
        (stats["total_predictions"] / 10) * 30 +  # Volume
        (stats["avg_confidence"] * 100) * 0.4 +  # Quality
        (len(stats["unique_emotions"]) / 8) * 100 * 0.2 +  # Diversity
        (streak / 7) * 10  # Consistency
    ))

    return {
        "total_predictions": stats["total_predictions"],
        "avg_confidence": round(stats["avg_confidence"], 3) if stats["avg_confidence"] else 0,
        "unique_emotions": len(stats["unique_emotions"]),
        "most_common_emotion": most_common_emotion,
        "prediction_streak": streak,
        "engagement_score": round(engagement_score, 1),
        "first_prediction": stats["first_prediction"].isoformat() if stats["first_prediction"] else None,
        "last_prediction": stats["last_prediction"].isoformat() if stats["last_prediction"] else None
    }

async def get_system_overview_metrics(days: int = 7) -> Dict[str, Any]:
    """Get system overview metrics for dashboard."""
    db = MongoDB.get_database()

    # Get recent activity
    recent_pipeline = [
        {
            PIPELINE_MATCH: {
                CREATED_AT: {PIPELINE_GTE: datetime.now(datetime.timezone.utc) - timedelta(days=days)}
            }
        },
        {
            PIPELINE_GROUP: {
                "_id": None,
                "total_predictions": {PIPELINE_SUM: 1},
                "unique_users": {PIPELINE_ADD_TO_SET: USER_ID},
                "avg_confidence": {PIPELINE_AVG: CONFIDENCE},
                "emotions": {PIPELINE_PUSH: EMOTION}
            }
        }
    ]

    recent_stats = await db[PREDICTIONS_COLLECTION].aggregate(recent_pipeline).to_list(length=1)

    if not recent_stats:
        return {
            "period_days": days,
            "total_predictions": 0,
            "active_users": 0,
            "avg_confidence": 0,
            "top_emotions": [],
            "predictions_trend": []
        }

    stats = recent_stats[0]

    # Get emotion distribution
    emotion_counts = {}
    for emotion in stats["emotions"]:
        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

    top_emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # Get daily trend for the period
    trend_pipeline = [
        {
            PIPELINE_MATCH: {
                CREATED_AT: {PIPELINE_GTE: datetime.now(datetime.timezone.utc) - timedelta(days=days)}
            }
        },
        {
            PIPELINE_GROUP: {
                "_id": {
                    PIPELINE_DATE: {
                        "format": "%Y-%m-%d",
                        "date": CREATED_AT
                    }
                },
                "count": {PIPELINE_SUM: 1}
            }
        },
        {PIPELINE_SORT: {"_id": 1}}
    ]

    trend_data = await db[PREDICTIONS_COLLECTION].aggregate(trend_pipeline).to_list(length=None)

    predictions_trend = [{"date": item["_id"], "count": item["count"]} for item in trend_data]

    return {
        "period_days": days,
        "total_predictions": stats["total_predictions"],
        "active_users": len(stats["unique_users"]),
        "avg_confidence": round(stats["avg_confidence"], 3) if stats["avg_confidence"] else 0,
        "top_emotions": [{"emotion": emotion, "count": count} for emotion, count in top_emotions],
        "predictions_trend": predictions_trend
    }
