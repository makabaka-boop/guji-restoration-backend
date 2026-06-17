from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'paper-types', views.PaperTypeViewSet)
router.register(r'binding-types', views.BindingTypeViewSet)
router.register(r'workstations', views.WorkstationViewSet)
router.register(r'books', views.BookViewSet)
router.register(r'work-orders', views.WorkOrderViewSet)
router.register(r'restoration-records', views.RestorationRecordViewSet)
router.register(r'review-records', views.ReviewRecordViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('statistics/dashboard/', views.statistics_dashboard, name='statistics_dashboard'),
    path('alerts/', views.alert_list, name='alert_list'),
]
