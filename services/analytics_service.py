from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models import User, Prediction, AudioFile, UserActivity, UserStatistics, PredictionAnalytics, SystemMetrics
from schema import UserStatisticsResponse, UserActivityResponse, PredictionAnalyticsResponse, SystemMetricsResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import logging
import json
from database_mongo import MongoDB, PREDICTIONS_COLLECTION, ANALYTICS_COLLECTION

# Constants for performance thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.8
LOW_CONFIDENCE_THRESHOLD = 0.5
PROCESSING_TIME_NORMALIZATION_FACTOR = 10
CONFIDENCE_WEIGHT = 0.7
PROCESSING_TIME_WEIGHT = 0.3

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def log_user_activity(self, user_id: int, action: str, details: Optional[dict] = None,
                         ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> bool:
        """Log user activity for analytics"""
        try:
            activity = UserActivity(
                user_id=user_id,
                action=action,
                details=json.dumps(details) if details else None,
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db.add(activity)
            self.db.commit()
            logger.info(f"Logged activity: {action} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to log user activity: {str(e)}")
            self.db.rollback()
            return False

    def get_user_statistics(self, user_id: int) -> UserStatisticsResponse:
        """Get or create user statistics"""
        try:
            # Try to get existing statistics
            stats = self.db.query(UserStatistics).filter(UserStatistics.user_id == user_id).first()

            if not stats:
                # Create new statistics
                stats = UserStatistics(user_id=user_id)
                self.db.add(stats)
                self.db.commit()
                self.db.refresh(stats)

            # Update statistics with current data
            self._update_user_statistics(stats)
            self.db.commit()
            self.db.refresh(stats)

            return stats
        except Exception as e:
            logger.error(f"Failed to get user statistics for user {user_id}: {str(e)}")
            self.db.rollback()
            raise

    def _update_user_statistics(self, stats: UserStatistics):
        """Update user statistics with current data"""
        user_id = stats.user_id

        # Count predictions
        prediction_count = self.db.query(func.count(Prediction.id)).filter(Prediction.user_id == user_id).scalar()
        stats.total_predictions = prediction_count

        # Count uploads
        upload_count = self.db.query(func.count(AudioFile.id)).filter(AudioFile.user_id == user_id).scalar()
        stats.total_uploads = upload_count

        # Count logins (from activities)
        login_count = self.db.query(func.count(UserActivity.id)).filter(
            UserActivity.user_id == user_id,
            UserActivity.action == "login"
        ).scalar()
        stats.total_logins = login_count

        # Calculate average confidence
        if prediction_count > 0:
            avg_confidence = self.db.query(func.avg(Prediction.confidence)).filter(
                Prediction.user_id == user_id,
                Prediction.confidence.isnot(None)
            ).scalar()
            stats.average_confidence = avg_confidence

        # Find most common emotion
        if prediction_count > 0:
            most_common = self.db.query(Prediction.emotion, func.count(Prediction.emotion)).filter(
                Prediction.user_id == user_id
            ).group_by(Prediction.emotion).order_by(desc(func.count(Prediction.emotion))).first()

            if most_common:
                stats.most_common_emotion = most_common[0]

        # Update last activity
        last_activity = self.db.query(UserActivity).filter(UserActivity.user_id == user_id).order_by(
            desc(UserActivity.created_at)
        ).first()
        if last_activity:
            stats.last_activity = last_activity.created_at

    def get_user_activity_history(self, user_id: int, limit: int = 50, offset: int = 0) -> List[UserActivityResponse]:
        """Get user activity history"""
        try:
            activities = self.db.query(UserActivity).filter(UserActivity.user_id == user_id).order_by(
                desc(UserActivity.created_at)
            ).offset(offset).limit(limit).all()

            return activities
        except Exception as e:
            logger.error(f"Failed to get activity history for user {user_id}: {str(e)}")
            return []

    def get_prediction_analytics(self, prediction_id: int) -> Optional[PredictionAnalyticsResponse]:
        """Get analytics for a specific prediction"""
        try:
            analytics = self.db.query(PredictionAnalytics).filter(
                PredictionAnalytics.prediction_id == prediction_id
            ).first()
            return analytics
        except Exception as e:
            logger.error(f"Failed to get prediction analytics for prediction {prediction_id}: {str(e)}")
            return None

    def log_prediction_analytics(self, prediction_id: int, model_version: Optional[str] = None,
                                processing_time: Optional[float] = None,
                                feature_extraction_time: Optional[float] = None,
                                model_inference_time: Optional[float] = None) -> bool:
        """Log analytics for a prediction"""
        try:
            analytics = PredictionAnalytics(
                prediction_id=prediction_id,
                model_version=model_version,
                processing_time=processing_time,
                feature_extraction_time=feature_extraction_time,
                model_inference_time=model_inference_time
            )
            self.db.add(analytics)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to log prediction analytics: {str(e)}")
            self.db.rollback()
            return False

    def get_system_metrics(self, metric_type: Optional[str] = None, limit: int = 100) -> List[SystemMetricsResponse]:
        """Get system metrics"""
        try:
            query = self.db.query(SystemMetrics)
            if metric_type:
                query = query.filter(SystemMetrics.metric_type == metric_type)

            metrics = query.order_by(desc(SystemMetrics.timestamp)).limit(limit).all()
            return metrics
        except Exception as e:
            logger.error(f"Failed to get system metrics: {str(e)}")
            return []

    def log_system_metric(self, metric_type: str, value: float, unit: Optional[str] = None) -> bool:
        """Log a system metric"""
        try:
            metric = SystemMetrics(
                metric_type=metric_type,
                value=value,
                unit=unit
            )
            self.db.add(metric)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to log system metric: {str(e)}")
            self.db.rollback()
            return False

    def get_user_engagement_stats(self) -> dict:
        """Get overall user engagement statistics"""
        try:
            total_users = self.db.query(func.count(User.id)).scalar()
            active_users_7d = self.db.query(func.count(func.distinct(UserActivity.user_id))).filter(
                UserActivity.created_at >= datetime.now(datetime.timezone.utc) - timedelta(days=7)
            ).scalar()
            active_users_30d = self.db.query(func.count(func.distinct(UserActivity.user_id))).filter(
                UserActivity.created_at >= datetime.now(datetime.timezone.utc) - timedelta(days=30)
            ).scalar()

            total_predictions = self.db.query(func.count(Prediction.id)).scalar()
            total_uploads = self.db.query(func.count(AudioFile.id)).scalar()

            return {
                "total_users": total_users,
                "active_users_7d": active_users_7d,
                "active_users_30d": active_users_30d,
                "total_predictions": total_predictions,
                "total_uploads": total_uploads,
                "predictions_per_user": total_predictions / total_users if total_users > 0 else 0,
                "uploads_per_user": total_uploads / total_users if total_users > 0 else 0
            }
        except Exception as e:
            logger.error(f"Failed to get user engagement stats: {str(e)}")
            return {}

    def get_emotion_distribution(self, user_id: Optional[int] = None, days: Optional[int] = None) -> dict:
        """Get emotion distribution for predictions"""
        try:
            query = self.db.query(Prediction.emotion, func.count(Prediction.emotion))

            if user_id:
                query = query.filter(Prediction.user_id == user_id)

            if days:
                query = query.filter(Prediction.created_at >= datetime.now(datetime.timezone.utc) - timedelta(days=days))

            distribution = query.group_by(Prediction.emotion).all()

            return dict(distribution)
        except Exception as e:
            logger.error(f"Failed to get emotion distribution: {str(e)}")
            return {}

    def cleanup_old_activities(self, days: int = 90) -> int:
        """Clean up old user activities (for GDPR compliance)"""
        try:
            cutoff_date = datetime.now(datetime.timezone.utc) - timedelta(days=days)
            deleted_count = self.db.query(UserActivity).filter(
                UserActivity.created_at < cutoff_date
            ).delete()
            self.db.commit()
            logger.info(f"Cleaned up {deleted_count} old user activities")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup old activities: {str(e)}")
            self.db.rollback()
            return 0


def _initialize_model_metrics() -> dict:
    """Initialize model performance metrics structure."""
    return {
        "total_predictions": 0,
        "total_confidence": 0,
        "high_confidence_count": 0,
        "low_confidence_count": 0,
        "processing_times": []
    }


def _initialize_daily_trend() -> dict:
    """Initialize daily trend structure."""
    return {
        "predictions": 0,
        "total_confidence": 0,
        "total_processing_time": 0
    }


def _process_prediction_for_models(pred: dict, model_performance: dict) -> None:
    """Process a single prediction for model performance aggregation."""
    model_version = pred.get("model_version", "unknown")
    confidence = pred.get("confidence", 0)
    
    if model_version not in model_performance:
        model_performance[model_version] = _initialize_model_metrics()

    metrics = model_performance[model_version]
    metrics["total_predictions"] += 1
    metrics["total_confidence"] += confidence

    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        metrics["high_confidence_count"] += 1
    elif confidence < LOW_CONFIDENCE_THRESHOLD:
        metrics["low_confidence_count"] += 1

    processing_time = pred.get("processing_time")
    if processing_time:
        metrics["processing_times"].append(processing_time)


def _process_prediction_for_daily_trends(pred: dict, daily_trends: dict) -> None:
    """Process a single prediction for daily trends aggregation."""
    created_at = pred.get("created_at")
    if not created_at:
        return

    date_key = created_at.date().isoformat()
    if date_key not in daily_trends:
        daily_trends[date_key] = _initialize_daily_trend()

    confidence = pred.get("confidence", 0)
    processing_time = pred.get("processing_time")

    daily_trends[date_key]["predictions"] += 1
    daily_trends[date_key]["total_confidence"] += confidence
    if processing_time:
        daily_trends[date_key]["total_processing_time"] += processing_time


def _calculate_model_metrics(metrics: dict) -> None:
    """Calculate derived metrics for model performance."""
    total = metrics["total_predictions"]
    
    if total > 0:
        metrics["avg_confidence"] = metrics["total_confidence"] / total
        metrics["avg_processing_time"] = (sum(metrics["processing_times"]) / 
                                         len(metrics["processing_times"]) 
                                         if metrics["processing_times"] else 0)
        metrics["high_confidence_ratio"] = metrics["high_confidence_count"] / total
        metrics["low_confidence_ratio"] = metrics["low_confidence_count"] / total
        
        # Simple performance score based on confidence and processing time
        processing_factor = 1 - (metrics["avg_processing_time"] / PROCESSING_TIME_NORMALIZATION_FACTOR)
        metrics["performance_score"] = ((metrics["avg_confidence"] * CONFIDENCE_WEIGHT) + 
                                       (processing_factor * PROCESSING_TIME_WEIGHT))
    else:
        metrics["avg_confidence"] = 0
        metrics["avg_processing_time"] = 0
        metrics["high_confidence_ratio"] = 0
        metrics["low_confidence_ratio"] = 0
        metrics["performance_score"] = 0

    # Remove intermediate fields
    del metrics["total_confidence"]
    del metrics["processing_times"]


def _calculate_daily_trends(trends: dict, date_key: str, predictions: list) -> None:
    """Calculate derived metrics for daily trends."""
    total = trends["predictions"]
    
    if total > 0:
        trends["avg_confidence"] = trends["total_confidence"] / total
        trends["avg_processing_time"] = trends["total_processing_time"] / total
        
        high_confidence_count = sum(
            1 for p in predictions 
            if (p.get("confidence", 0) >= HIGH_CONFIDENCE_THRESHOLD and 
                p.get("created_at") and 
                p["created_at"].date().isoformat() == date_key)
        )
        trends["high_confidence_ratio"] = high_confidence_count / total
    else:
        trends["avg_confidence"] = 0
        trends["avg_processing_time"] = 0
        trends["high_confidence_ratio"] = 0

    del trends["total_confidence"]
    del trends["total_processing_time"]


async def get_ml_model_performance(days: int = 30) -> dict:
    """Get ML model performance analytics from MongoDB."""
    db = MongoDB.get_database()
    start_date = datetime.now(datetime.timezone.utc) - timedelta(days=days)

    # Get all predictions in the period
    predictions = await db[PREDICTIONS_COLLECTION].find(
        {"created_at": {"$gte": start_date}}
    ).to_list(length=None)

    # Group by model_version and daily trends
    model_performance = {}
    daily_trends = {}

    for pred in predictions:
        _process_prediction_for_models(pred, model_performance)
        _process_prediction_for_daily_trends(pred, daily_trends)

    # Calculate averages and ratios for models
    for metrics in model_performance.values():
        _calculate_model_metrics(metrics)

    # Calculate averages and ratios for daily trends
    for date_key, trends in daily_trends.items():
        _calculate_daily_trends(trends, date_key, predictions)

    return {
        "model_performance": model_performance,
        "daily_trends": daily_trends
    }


async def get_system_analytics(days: int = 30) -> dict:
    """Get system analytics from MongoDB."""
    db = MongoDB.get_database()
    start_date = datetime.now(datetime.timezone.utc) - timedelta(days=days)

    # Get all predictions in the period
    predictions = await db[PREDICTIONS_COLLECTION].find(
        {"created_at": {"$gte": start_date}}
    ).to_list(length=None)

    total_predictions = len(predictions)
    active_users = len({pred.get("user_id") for pred in predictions if pred.get("user_id")})

    # Emotion distribution
    emotion_distribution = {}
    daily_activity = {}

    for pred in predictions:
        emotion = pred.get("emotion")
        created_at = pred.get("created_at")

        if emotion:
            emotion_distribution[emotion] = emotion_distribution.get(emotion, 0) + 1

        if created_at:
            date_key = created_at.date().isoformat()
            daily_activity[date_key] = daily_activity.get(date_key, 0) + 1

    return {
        "period_days": days,
        "total_predictions": total_predictions,
        "active_users": active_users,
        "emotion_distribution": emotion_distribution,
        "daily_activity": daily_activity
    }


def _calculate_avg_confidence(predictions: list) -> float:
    """Calculate average confidence from predictions."""
    confidences = [p.get("confidence", 0) for p in predictions if p.get("confidence") is not None]
    return sum(confidences) / len(confidences) if confidences else 0


def _calculate_emotion_distribution(predictions: list) -> tuple:
    """Calculate emotion distribution and return counts and most common."""
    emotion_counts = {}
    for pred in predictions:
        emotion = pred.get("emotion")
        if emotion:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
    
    most_common = max(emotion_counts, key=emotion_counts.get) if emotion_counts else None
    return most_common, emotion_counts


def _calculate_prediction_streak(predictions: list) -> int:
    """Calculate consecutive days with predictions."""
    prediction_dates = sorted({p.get("created_at").date() for p in predictions if p.get("created_at")}, reverse=True)
    streak = 0
    current_date = datetime.now(datetime.timezone.utc).date()
    
    for date in prediction_dates:
        if date == current_date or date == current_date - timedelta(days=streak):
            streak += 1
            current_date = date
        else:
            break
    
    return streak


def _get_first_last_predictions(predictions: list) -> tuple:
    """Get first and last prediction timestamps."""
    valid_dates = [p.get("created_at") for p in predictions if p.get("created_at")]
    first = min(valid_dates) if valid_dates else None
    last = max(valid_dates) if valid_dates else None
    return first, last


def _calculate_weekly_activity(predictions: list) -> dict:
    """Calculate weekly activity metrics."""
    weekly_activity = {}
    week_ago = datetime.now(datetime.timezone.utc) - timedelta(days=7)
    
    # Initialize 7 days
    for i in range(7):
        date = (datetime.now(datetime.timezone.utc) - timedelta(days=i)).date()
        weekly_activity[date.isoformat()] = {
            "predictions": 0,
            "avg_confidence": 0,
            "total_confidence": 0
        }
    
    # Populate from predictions
    for pred in predictions:
        created_at = pred.get("created_at")
        if not created_at or created_at < week_ago:
            continue
            
        date_key = created_at.date().isoformat()
        if date_key not in weekly_activity:
            continue
            
        weekly_activity[date_key]["predictions"] += 1
        weekly_activity[date_key]["total_confidence"] += pred.get("confidence", 0)
    
    # Calculate averages
    for activity in weekly_activity.values():
        if activity["predictions"] > 0:
            activity["avg_confidence"] = activity["total_confidence"] / activity["predictions"]
        del activity["total_confidence"]
    
    return weekly_activity


async def get_user_insights(user_id: str) -> dict:
    """Get user insights from MongoDB."""
    db = MongoDB.get_database()

    # Get all predictions for the user
    predictions = await db[PREDICTIONS_COLLECTION].find(
        {"user_id": user_id}
    ).sort("created_at", -1).to_list(length=None)

    total_predictions = len(predictions)

    if total_predictions == 0:
        return {
            "user_id": user_id,
            "total_predictions": 0,
            "avg_confidence": 0,
            "most_common_emotion": None,
            "prediction_streak": 0,
            "first_prediction": None,
            "last_prediction": None,
            "weekly_activity": {},
            "emotion_distribution": {}
        }

    avg_confidence = _calculate_avg_confidence(predictions)
    most_common_emotion, emotion_counts = _calculate_emotion_distribution(predictions)
    streak = _calculate_prediction_streak(predictions)
    first_prediction, last_prediction = _get_first_last_predictions(predictions)
    weekly_activity = _calculate_weekly_activity(predictions)

    return {
        "user_id": user_id,
        "total_predictions": total_predictions,
        "avg_confidence": avg_confidence,
        "most_common_emotion": most_common_emotion,
        "prediction_streak": streak,
        "first_prediction": first_prediction,
        "last_prediction": last_prediction,
        "weekly_activity": weekly_activity,
        "emotion_distribution": emotion_counts
    }
