from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    UserViewSet, BookVolumeViewSet, WorkOrderViewSet,
    ReviewRecordViewSet, AlertViewSet,
    statistics_rework_distribution,
    statistics_pending_review,
    statistics_cycle_ranges,
    run_alerts,
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'books', BookVolumeViewSet)
router.register(r'work-orders', WorkOrderViewSet)
router.register(r'reviews', ReviewRecordViewSet)
router.register(r'alerts', AlertViewSet)

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/alerts/run/', run_alerts, name='run_alerts'),
    path('api/statistics/rework-distribution/', statistics_rework_distribution, name='stats_rework'),
    path('api/statistics/pending-review/', statistics_pending_review, name='stats_pending_review'),
    path('api/statistics/cycle-ranges/', statistics_cycle_ranges, name='stats_cycle'),
    path('api/', include(router.urls)),
]
