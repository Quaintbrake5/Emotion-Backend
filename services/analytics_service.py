from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models import User, Prediction, AudioFile, UserActivity, UserStatistics, PredictionAnalytics, SystemMetrics
from schema import UserStatisticsResponse, UserActivityResponse, PredictionAnalyticsResponse, SystemMetricsResponse
from typing import List, Optional
from datetime import datetime, timedelta
import logging
import json

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
                UserActivity.created_at >= datetime.utcnow() - timedelta(days=7)
            ).scalar()
            active_users_30d = self.db.query(func.count(func.distinct(UserActivity.user_id))).filter(
                UserActivity.created_at >= datetime.utcnow() - timedelta(days=30)
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
                query = query.filter(Prediction.created_at >= datetime.utcnow() - timedelta(days=days))

            distribution = query.group_by(Prediction.emotion).all()

            return {emotion: count for emotion, count in distribution}
        except Exception as e:
            logger.error(f"Failed to get emotion distribution: {str(e)}")
            return {}

    def cleanup_old_activities(self, days: int = 90) -> int:
        """Clean up old user activities (for GDPR compliance)"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
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
