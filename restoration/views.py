from django.utils import timezone
from django.db.models import Count, Q, F, ExpressionWrapper, fields as db_fields, Avg, Case, When, IntegerField
from django.db.models.functions import TruncDay
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User, BookVolume, WorkOrder, ReviewRecord, Alert
from .serializers import (
    UserSerializer, UserCreateSerializer,
    BookVolumeSerializer,
    WorkOrderListSerializer, WorkOrderDetailSerializer, WorkOrderCreateSerializer,
    RestorationSubmitSerializer,
    ReviewRecordSerializer, ReviewSubmitSerializer,
    AlertSerializer,
    StatusTransitionSerializer,
    ReworkSubmitSerializer,
)
from .permissions import IsAdmin, IsAdminOrRestorer, IsAdminOrReviewer
from .alerts import run_all_alerts


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer


class BookVolumeViewSet(viewsets.ModelViewSet):
    queryset = BookVolume.objects.select_related('responsible').all()
    serializer_class = BookVolumeSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['code', 'paper_type', 'station', 'responsible']
    search_fields = ['code', 'paper_type']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]


class WorkOrderViewSet(viewsets.ModelViewSet):
    queryset = WorkOrder.objects.select_related('book', 'book__responsible', 'operator').all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ['book__code', 'book__paper_type', 'book__station', 'status', 'operator']
    search_fields = ['book__code']

    def get_serializer_class(self):
        if self.action == 'create':
            return WorkOrderCreateSerializer
        if self.action == 'retrieve':
            return WorkOrderDetailSerializer
        return WorkOrderListSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsAdmin()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAdmin()]
        if self.action == 'transition':
            return [IsAuthenticated(), IsAdmin()]
        if self.action in ('accept', 'submit_restoration', 'complete_pressing'):
            return [IsAuthenticated(), IsAdminOrRestorer()]
        if self.action in ('submit_review', 'rework'):
            return [IsAuthenticated(), IsAdminOrReviewer()]
        if self.action in ('suspend', 'resume'):
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'], url_path='accept')
    def accept(self, request, pk=None):
        order = self.get_object()
        if order.status != WorkOrder.STATUS_PENDING:
            return Response({'detail': '只有待接收状态的工单才能接收'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role not in ('admin', 'restorer'):
            return Response({'detail': '只有管理员或修护师可以接收工单'}, status=status.HTTP_403_FORBIDDEN)
        order.status = WorkOrder.STATUS_PROCESSING
        order.operator = request.user
        order.save()
        return Response(WorkOrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'], url_path='submit-restoration')
    def submit_restoration(self, request, pk=None):
        order = self.get_object()
        if order.status not in (WorkOrder.STATUS_PROCESSING, WorkOrder.STATUS_REWORK):
            return Response({'detail': '只有处理中或返工中的工单才能提交修护信息'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role not in ('admin', 'restorer'):
            return Response({'detail': '只有管理员或修护师可以提交修护信息'}, status=status.HTTP_403_FORBIDDEN)
        serializer = RestorationSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field in ('page_removal', 'paper_repair', 'pressing', 'binding',
                       'damage_description', 'processing_notes'):
            val = serializer.validated_data.get(field, '')
            if val:
                setattr(order, field, val)
        order.save()
        return Response(WorkOrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'], url_path='complete-pressing')
    def complete_pressing(self, request, pk=None):
        order = self.get_object()
        if order.status not in (WorkOrder.STATUS_PROCESSING, WorkOrder.STATUS_PENDING_PRESSING):
            return Response({'detail': '当前状态不允许完成压平'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role not in ('admin', 'restorer'):
            return Response({'detail': '只有管理员或修护师可以完成压平'}, status=status.HTTP_403_FORBIDDEN)
        order.status = WorkOrder.STATUS_PENDING_REVIEW
        order.pressing_completed_at = timezone.now()
        order.save()
        run_all_alerts()
        return Response(WorkOrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'], url_path='submit-review')
    def submit_review(self, request, pk=None):
        order = self.get_object()
        if order.status != WorkOrder.STATUS_PENDING_REVIEW:
            return Response({'detail': '只有待复核状态的工单才能提交复核'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role not in ('admin', 'reviewer'):
            return Response({'detail': '只有管理员或复核员可以提交复核'}, status=status.HTTP_403_FORBIDDEN)
        serializer = ReviewSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = ReviewRecord.objects.create(
            work_order=order,
            reviewer=request.user,
            flatness=serializer.validated_data['flatness'],
            page_order_check=serializer.validated_data['page_order_check'],
            cover_status=serializer.validated_data['cover_status'],
            conclusion=serializer.validated_data['conclusion'],
            remark=serializer.validated_data.get('remark', ''),
        )
        if serializer.validated_data['conclusion'] == 'pass':
            order.status = WorkOrder.STATUS_CAN_STORE
        else:
            order.status = WorkOrder.STATUS_REWORK
            order.rework_count += 1
        order.save()
        run_all_alerts()
        return Response(ReviewRecordSerializer(review).data)

    @action(detail=True, methods=['post'], url_path='rework')
    def rework(self, request, pk=None):
        order = self.get_object()
        if order.status not in (WorkOrder.STATUS_PENDING_REVIEW, WorkOrder.STATUS_CAN_STORE):
            return Response({'detail': '当前状态不允许发起返工'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role not in ('admin', 'reviewer'):
            return Response({'detail': '只有管理员或复核员可以发起返工'}, status=status.HTTP_403_FORBIDDEN)
        serializer = ReworkSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order.status = WorkOrder.STATUS_REWORK
        order.rework_count += 1
        order.rework_reason = serializer.validated_data['rework_reason']
        order.save()
        return Response(WorkOrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'], url_path='suspend')
    def suspend(self, request, pk=None):
        order = self.get_object()
        if order.status in (WorkOrder.STATUS_CAN_STORE,):
            return Response({'detail': '已入库的工单不能暂停'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role != 'admin':
            return Response({'detail': '只有管理员可以暂停工单'}, status=status.HTTP_403_FORBIDDEN)
        order._previous_status = order.status
        order.status = WorkOrder.STATUS_SUSPENDED
        order.save()
        return Response(WorkOrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'], url_path='resume')
    def resume(self, request, pk=None):
        order = self.get_object()
        if order.status != WorkOrder.STATUS_SUSPENDED:
            return Response({'detail': '只有暂停处理的工单才能恢复'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role != 'admin':
            return Response({'detail': '只有管理员可以恢复工单'}, status=status.HTTP_403_FORBIDDEN)
        order.status = WorkOrder.STATUS_PROCESSING
        order.save()
        return Response(WorkOrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        order = self.get_object()
        serializer = StatusTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        valid = self._validate_transition(order.status, new_status)
        if not valid:
            return Response({'detail': f'不允许从 {order.get_status_display()} 转换到 {dict(WorkOrder.STATUS_CHOICES)[new_status]}'},
                            status=status.HTTP_400_BAD_REQUEST)
        order.status = new_status
        if new_status == WorkOrder.STATUS_PENDING_REVIEW:
            order.pressing_completed_at = timezone.now()
        order.save()
        run_all_alerts()
        return Response(WorkOrderDetailSerializer(order).data)

    def _validate_transition(self, current, target):
        transitions = {
            WorkOrder.STATUS_PENDING: [WorkOrder.STATUS_PROCESSING],
            WorkOrder.STATUS_PROCESSING: [WorkOrder.STATUS_PENDING_PRESSING, WorkOrder.STATUS_PENDING_REVIEW, WorkOrder.STATUS_SUSPENDED],
            WorkOrder.STATUS_PENDING_PRESSING: [WorkOrder.STATUS_PENDING_REVIEW, WorkOrder.STATUS_SUSPENDED],
            WorkOrder.STATUS_PENDING_REVIEW: [WorkOrder.STATUS_CAN_STORE, WorkOrder.STATUS_REWORK, WorkOrder.STATUS_SUSPENDED],
            WorkOrder.STATUS_REWORK: [WorkOrder.STATUS_PENDING_PRESSING, WorkOrder.STATUS_PENDING_REVIEW, WorkOrder.STATUS_SUSPENDED],
            WorkOrder.STATUS_SUSPENDED: [WorkOrder.STATUS_PROCESSING],
        }
        return target in transitions.get(current, [])


class ReviewRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReviewRecord.objects.select_related('work_order', 'reviewer').all()
    serializer_class = ReviewRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['work_order', 'reviewer', 'conclusion']


class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Alert.objects.select_related('work_order', 'work_order__book').all()
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['alert_type', 'is_resolved']

    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve(self, request, pk=None):
        alert = self.get_object()
        if request.user.role != 'admin':
            return Response({'detail': '只有管理员可以处理预警'}, status=status.HTTP_403_FORBIDDEN)
        alert.is_resolved = True
        alert.save()
        return Response(AlertSerializer(alert).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def statistics_rework_distribution(request):
    rework_orders = WorkOrder.objects.filter(
        rework_count__gt=0
    ).exclude(rework_reason='').values('rework_reason').annotate(
        count=Count('id')
    ).order_by('-count')
    return Response(list(rework_orders))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def statistics_pending_review(request):
    orders = WorkOrder.objects.filter(
        status=WorkOrder.STATUS_PENDING_REVIEW
    ).select_related('book', 'operator')
    data = []
    for order in orders:
        overdue = False
        if order.pressing_completed_at:
            deadline = order.pressing_completed_at + timezone.timedelta(
                days=order.book.review_interval_days
            )
            overdue = timezone.now() > deadline
        data.append({
            'id': order.id,
            'book_code': order.book.code,
            'paper_type': order.book.paper_type,
            'operator': order.operator.username if order.operator else None,
            'pressing_completed_at': order.pressing_completed_at,
            'overdue': overdue,
            'created_at': order.created_at,
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def statistics_cycle_ranges(request):
    completed = WorkOrder.objects.filter(
        status=WorkOrder.STATUS_CAN_STORE
    ).annotate(
        cycle_days=ExpressionWrapper(
            F('updated_at') - F('created_at'),
            output_field=db_fields.DurationField()
        )
    )
    ranges = [
        {'label': '0-3天', 'min': 0, 'max': 3},
        {'label': '4-7天', 'min': 4, 'max': 7},
        {'label': '8-14天', 'min': 8, 'max': 14},
        {'label': '15-30天', 'min': 15, 'max': 30},
        {'label': '30天以上', 'min': 31, 'max': None},
    ]
    result = []
    for r in ranges:
        qs = completed
        if r['max'] is not None:
            count = qs.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=r['max']),
                created_at__lte=timezone.now() - timezone.timedelta(days=r['min']),
            ).count()
        else:
            count = qs.filter(
                created_at__lte=timezone.now() - timezone.timedelta(days=r['min']),
            ).count()
        result.append({'range': r['label'], 'count': count})

    all_completed = WorkOrder.objects.filter(status=WorkOrder.STATUS_CAN_STORE)
    total = all_completed.count()
    if total > 0:
        avg_cycle = all_completed.annotate(
            cycle=ExpressionWrapper(F('updated_at') - F('created_at'), output_field=db_fields.DurationField())
        ).aggregate(avg=Avg('cycle'))['avg']
        avg_days = avg_cycle.days if avg_cycle else 0
    else:
        avg_days = 0

    return Response({
        'distribution': result,
        'total_completed': total,
        'average_cycle_days': avg_days,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def run_alerts(request):
    run_all_alerts()
    return Response({'detail': '预警检测已执行'})
