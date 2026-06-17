from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    MyTokenObtainPairView, user_info,
    UserViewSet, PaperTypeViewSet, BindingTypeViewSet,
    WorkStationViewSet, ResponsiblePersonViewSet, BookViewSet,
    WorkOrderViewSet, StatisticsView, AlertView
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'paper-types', PaperTypeViewSet, basename='paper-type')
router.register(r'binding-types', BindingTypeViewSet, basename='binding-type')
router.register(r'work-stations', WorkStationViewSet, basename='work-station')
router.register(r'responsible-persons', ResponsiblePersonViewSet, basename='responsible-person')
router.register(r'books', BookViewSet, basename='book')
router.register(r'work-orders', WorkOrderViewSet, basename='work-order')

urlpatterns = [
    path('auth/login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/user-info/', user_info, name='user_info'),
    path('statistics/', StatisticsView.as_view(), name='statistics'),
    path('alerts/', AlertView.as_view(), name='alerts'),
    path('', include(router.urls)),
]
