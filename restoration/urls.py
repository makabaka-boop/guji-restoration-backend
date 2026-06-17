from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomTokenObtainPairView,
    UserViewSet, PaperTypeViewSet, BindingTypeViewSet, StationViewSet,
    BookViewSet, WorkOrderViewSet,
    StatisticsView, AnomalyView, current_user, dashboard_summary,
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'paper-types', PaperTypeViewSet)
router.register(r'binding-types', BindingTypeViewSet)
router.register(r'stations', StationViewSet)
router.register(r'books', BookViewSet)
router.register(r'work-orders', WorkOrderViewSet)

urlpatterns = [
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', current_user, name='current_user'),
    path('dashboard/', dashboard_summary, name='dashboard_summary'),
    path('statistics/', StatisticsView.as_view(), name='statistics'),
    path('anomalies/', AnomalyView.as_view(), name='anomalies'),
    path('', include(router.urls)),
]
