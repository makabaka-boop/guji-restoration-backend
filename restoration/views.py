from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from .models import (
    User, PaperType, BindingType, Workstation, Book,
    WorkOrder, RestorationRecord, ReviewRecord, StatusLog
)
from .serializers import (
    UserSerializer, PaperTypeSerializer, BindingTypeSerializer,
    WorkstationSerializer, BookSerializer, BookListSerializer,
    WorkOrderSerializer, WorkOrderDetailSerializer, WorkOrderCreateSerializer,
    RestorationRecordSerializer, ReviewRecordSerializer, StatusLogSerializer
)


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == User.ROLE_ADMIN


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.ROLE_ADMIN


class IsRestorer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.ROLE_RESTORER


class IsReviewer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.ROLE_REVIEWER


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'first_name', 'last_name', 'email']


class PaperTypeViewSet(viewsets.ModelViewSet):
    queryset = PaperType.objects.all()
    serializer_class = PaperTypeSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [SearchFilter]
    search_fields = ['name']


class BindingTypeViewSet(viewsets.ModelViewSet):
    queryset = BindingType.objects.all()
    serializer_class = BindingTypeSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [SearchFilter]
    search_fields = ['name']


class WorkstationViewSet(viewsets.ModelViewSet):
    queryset = Workstation.objects.all()
    serializer_class = WorkstationSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [SearchFilter]
    search_fields = ['name']


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['paper_type', 'binding_type']
    search_fields = ['book_no', 'title']
    ordering_fields = ['book_no', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return BookListSerializer
        return BookSerializer


class WorkOrderViewSet(viewsets.ModelViewSet):
    queryset = WorkOrder.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'workstation', 'restorer', 'reviewer']
    search_fields = ['book__book_no', 'book__title']
    ordering_fields = ['created_at', 'updated_at', 'review_due_at']

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'book', 'book__paper_type', 'workstation', 'restorer', 'reviewer'
        )
        book_no = self.request.query_params.get('book_no')
        if book_no:
            queryset = queryset.filter(book__book_no__icontains=book_no)

        paper_type = self.request.query_params.get('paper_type')
        if paper_type:
            queryset = queryset.filter(book__paper_type_id=paper_type)

        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return WorkOrderCreateSerializer
        if self.action in ['retrieve', 'detail']:
            return WorkOrderDetailSerializer
        return WorkOrderSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role != User.ROLE_ADMIN:
            return Response({'detail': '无权限创建工单'}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        work_order = serializer.save()
        StatusLog.objects.create(
            work_order=work_order,
            from_status=None,
            to_status=work_order.status,
            operator=request.user,
            remark='创建工单'
        )
        headers = self.get_success_headers(serializer.data)
        return Response(WorkOrderSerializer(work_order).data,
                        status=status.HTTP_201_CREATED, headers=headers)

    def _change_status(self, request, pk, target_status, remark=''):
        work_order = self.get_object()
        old_status = work_order.status
        work_order.status = target_status
        now = timezone.now()

        if target_status == WorkOrder.STATUS_PROCESSING and not work_order.started_at:
            work_order.started_at = now
            if not work_order.received_at:
                work_order.received_at = now

        if target_status == WorkOrder.STATUS_PENDING_PRESSING:
            pass

        if target_status == WorkOrder.STATUS_PENDING_REVIEW:
            work_order.pressing_completed_at = now
            review_due = now + timedelta(days=work_order.review_interval_days)
            work_order.review_due_at = review_due

        if target_status == WorkOrder.STATUS_READY_STORAGE:
            work_order.completed_at = now

        if target_status == WorkOrder.STATUS_SUSPENDED:
            work_order.suspended_at = now

        if target_status == WorkOrder.STATUS_REWORKING:
            work_order.rework_count += 1

        work_order.save()

        StatusLog.objects.create(
            work_order=work_order,
            from_status=old_status,
            to_status=target_status,
            operator=request.user,
            remark=remark
        )
        return work_order

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def receive(self, request, pk=None):
        work_order = self.get_object()
        if work_order.status != WorkOrder.STATUS_PENDING_RECEIPT:
            return Response({'detail': '当前状态不可接收'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role != User.ROLE_RESTORER:
            return Response({'detail': '仅修护师可接收'}, status=status.HTTP_403_FORBIDDEN)
        if work_order.restorer_id != request.user.id:
            return Response({'detail': '仅指定责任人可接收该工单'}, status=status.HTTP_403_FORBIDDEN)
        work_order = self._change_status(request, pk, WorkOrder.STATUS_PROCESSING, '接收工单')
        return Response(WorkOrderSerializer(work_order).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_restoration(self, request, pk=None):
        work_order = self.get_object()
        if work_order.status not in [WorkOrder.STATUS_PROCESSING, WorkOrder.STATUS_REWORKING]:
            return Response({'detail': '当前状态不可提交修护记录'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role != User.ROLE_RESTORER:
            return Response({'detail': '仅修护师可提交'}, status=status.HTTP_403_FORBIDDEN)
        if work_order.restorer_id != request.user.id:
            return Response({'detail': '仅指定责任人可提交修护记录'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        data['work_order'] = work_order.id
        data['restorer'] = request.user.id
        serializer = RestorationRecordSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(restorer=request.user, work_order=work_order)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def to_pressing(self, request, pk=None):
        work_order = self.get_object()
        if work_order.status not in [WorkOrder.STATUS_PROCESSING, WorkOrder.STATUS_REWORKING]:
            return Response({'detail': '当前状态不可进入压平'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role != User.ROLE_RESTORER:
            return Response({'detail': '仅修护师可操作'}, status=status.HTTP_403_FORBIDDEN)
        if work_order.restorer_id != request.user.id:
            return Response({'detail': '仅指定责任人可操作压平'}, status=status.HTTP_403_FORBIDDEN)
        work_order = self._change_status(request, pk, WorkOrder.STATUS_PENDING_PRESSING, '进入压平')
        return Response(WorkOrderSerializer(work_order).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def pressing_done(self, request, pk=None):
        work_order = self.get_object()
        if work_order.status != WorkOrder.STATUS_PENDING_PRESSING:
            return Response({'detail': '当前状态不可完成压平'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role != User.ROLE_RESTORER:
            return Response({'detail': '仅修护师可操作'}, status=status.HTTP_403_FORBIDDEN)
        if work_order.restorer_id != request.user.id:
            return Response({'detail': '仅指定责任人可完成压平'}, status=status.HTTP_403_FORBIDDEN)
        work_order = self._change_status(request, pk, WorkOrder.STATUS_PENDING_REVIEW, '压平完成，待复核')
        return Response(WorkOrderSerializer(work_order).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_review(self, request, pk=None):
        work_order = self.get_object()
        if work_order.status != WorkOrder.STATUS_PENDING_REVIEW:
            return Response({'detail': '当前状态不可提交复核'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role != User.ROLE_REVIEWER:
            return Response({'detail': '仅复核员可提交'}, status=status.HTTP_403_FORBIDDEN)
        if work_order.reviewer_id and work_order.reviewer_id != request.user.id:
            return Response({'detail': '仅指定复核员可复核该工单'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        data['work_order'] = work_order.id
        data['reviewer'] = request.user.id
        serializer = ReviewRecordSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(reviewer=request.user, work_order=work_order)

        if review.conclusion == ReviewRecord.CONCLUSION_PASS:
            self._change_status(request, pk, WorkOrder.STATUS_READY_STORAGE, '复核通过')
        elif review.conclusion == ReviewRecord.CONCLUSION_REWORK:
            work_order.rework_reason = review.rework_reason
            work_order.save()
            self._change_status(request, pk, WorkOrder.STATUS_REWORKING,
                                f'复核返工: {review.rework_reason}')

        return Response(ReviewRecordSerializer(review).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def suspend(self, request, pk=None):
        work_order = self.get_object()
        if request.user.role != User.ROLE_ADMIN:
            return Response({'detail': '仅管理员可暂停'}, status=status.HTTP_403_FORBIDDEN)
        if work_order.status == WorkOrder.STATUS_SUSPENDED:
            return Response({'detail': '工单已暂停'}, status=status.HTTP_400_BAD_REQUEST)
        work_order = self._change_status(request, pk, WorkOrder.STATUS_SUSPENDED,
                                         request.data.get('remark', '暂停处理'))
        return Response(WorkOrderSerializer(work_order).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def resume(self, request, pk=None):
        work_order = self.get_object()
        if request.user.role != User.ROLE_ADMIN:
            return Response({'detail': '仅管理员可恢复'}, status=status.HTTP_403_FORBIDDEN)
        if work_order.status != WorkOrder.STATUS_SUSPENDED:
            return Response({'detail': '仅暂停状态可恢复'}, status=status.HTTP_400_BAD_REQUEST)
        resume_status = request.data.get('resume_status', WorkOrder.STATUS_PROCESSING)
        work_order = self._change_status(request, pk, resume_status,
                                         request.data.get('remark', '恢复处理'))
        return Response(WorkOrderSerializer(work_order).data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def status_logs(self, request, pk=None):
        work_order = self.get_object()
        logs = work_order.status_logs.all()
        serializer = StatusLogSerializer(logs, many=True)
        return Response(serializer.data)


class RestorationRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RestorationRecord.objects.all()
    serializer_class = RestorationRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['work_order', 'restorer']


class ReviewRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReviewRecord.objects.all()
    serializer_class = ReviewRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['work_order', 'reviewer', 'conclusion']


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def statistics_dashboard(request):
    now = timezone.now()

    rework_records = ReviewRecord.objects.filter(
        conclusion=ReviewRecord.CONCLUSION_REWORK
    ).values('rework_reason').annotate(count=Count('id')).order_by('-count')
    rework_reason_dist = [{'reason': item['rework_reason'] or '未填写', 'count': item['count']}
                          for item in rework_records]

    pending_review = WorkOrder.objects.filter(
        status=WorkOrder.STATUS_PENDING_REVIEW
    ).select_related('book', 'reviewer')
    pending_review_list = [
        {
            'id': wo.id,
            'book_no': wo.book.book_no,
            'book_title': wo.book.title,
            'reviewer': wo.reviewer.get_full_name() if wo.reviewer else '',
            'pressing_completed_at': wo.pressing_completed_at,
            'review_due_at': wo.review_due_at,
            'overdue': wo.review_due_at and wo.review_due_at < now
        }
        for wo in pending_review
    ]

    completed_orders = WorkOrder.objects.filter(
        status=WorkOrder.STATUS_READY_STORAGE,
        started_at__isnull=False,
        completed_at__isnull=False
    )
    cycle_data = []
    for wo in completed_orders:
        if wo.started_at and wo.completed_at:
            days = (wo.completed_at - wo.started_at).days
            cycle_data.append(days)

    if cycle_data:
        cycle_data.sort()
        avg_cycle = sum(cycle_data) / len(cycle_data)
        min_cycle = cycle_data[0]
        max_cycle = cycle_data[-1]
        median_idx = len(cycle_data) // 2
        median_cycle = cycle_data[median_idx] if len(cycle_data) % 2 == 1 \
            else (cycle_data[median_idx - 1] + cycle_data[median_idx]) / 2

        def count_range(low, high):
            return sum(1 for d in cycle_data if low <= d < high)

        cycle_intervals = [
            {'range': '0-3天', 'count': count_range(0, 3)},
            {'range': '3-7天', 'count': count_range(3, 7)},
            {'range': '7-14天', 'count': count_range(7, 14)},
            {'range': '14-30天', 'count': count_range(14, 30)},
            {'range': '30天以上', 'count': sum(1 for d in cycle_data if d >= 30)},
        ]
    else:
        avg_cycle = 0
        min_cycle = 0
        max_cycle = 0
        median_cycle = 0
        cycle_intervals = []

    total_orders = WorkOrder.objects.count()
    status_distribution = WorkOrder.objects.values('status').annotate(
        count=Count('id')
    )
    status_counts = {item['status']: item['count'] for item in status_distribution}

    return Response({
        'total_orders': total_orders,
        'status_distribution': [
            {'status': s[0], 'label': s[1], 'count': status_counts.get(s[0], 0)}
            for s in WorkOrder.STATUS_CHOICES
        ],
        'rework_reason_distribution': rework_reason_dist,
        'pending_review_orders': pending_review_list,
        'processing_cycle': {
            'avg_days': round(avg_cycle, 1),
            'min_days': min_cycle,
            'max_days': max_cycle,
            'median_days': median_cycle,
            'total_completed': len(cycle_data),
            'intervals': cycle_intervals,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def alert_list(request):
    now = timezone.now()
    alerts = []

    overdue_reviews = WorkOrder.objects.filter(
        status=WorkOrder.STATUS_PENDING_REVIEW,
        review_due_at__lt=now
    ).select_related('book', 'reviewer')
    for wo in overdue_reviews:
        overdue_days = (now - wo.review_due_at).days if wo.review_due_at else 0
        alerts.append({
            'type': 'overdue_review',
            'level': 'warning',
            'message': f'书册 {wo.book.book_no} 复核超期 {overdue_days} 天',
            'work_order_id': wo.id,
            'book_no': wo.book.book_no,
            'detail': {
                'reviewer': wo.reviewer.get_full_name() if wo.reviewer else '',
                'review_due_at': wo.review_due_at,
                'overdue_days': overdue_days,
            }
        })

    paper_rework_stats = ReviewRecord.objects.filter(
        conclusion=ReviewRecord.CONCLUSION_REWORK,
        work_order__status__in=[WorkOrder.STATUS_REWORKING, WorkOrder.STATUS_READY_STORAGE]
    ).values(
        'work_order__book__paper_type__name',
        'work_order__book__paper_type_id'
    ).annotate(
        rework_count=Count('id'),
        order_count=Count('work_order_id', distinct=True)
    )

    for item in paper_rework_stats:
        if item['order_count'] >= 3:
            rework_rate = item['rework_count'] / item['order_count']
            if rework_rate >= 0.3:
                alerts.append({
                    'type': 'high_rework_rate',
                    'level': 'warning',
                    'message': f'纸张类型「{item["work_order__book__paper_type__name"]}」返工率偏高',
                    'paper_type_id': item['work_order__book__paper_type_id'],
                    'detail': {
                        'paper_type': item['work_order__book__paper_type__name'],
                        'order_count': item['order_count'],
                        'rework_count': item['rework_count'],
                        'rework_rate': round(rework_rate * 100, 1),
                    }
                })

    no_review_after_pressing = WorkOrder.objects.filter(
        pressing_completed_at__isnull=False,
        status=WorkOrder.STATUS_PENDING_REVIEW,
        review_records__isnull=True
    ).select_related('book', 'reviewer').distinct()
    for wo in no_review_after_pressing:
        days_passed = (now - wo.pressing_completed_at).days if wo.pressing_completed_at else 0
        alerts.append({
            'type': 'no_review_after_pressing',
            'level': 'info',
            'message': f'书册 {wo.book.book_no} 压平完成后待复核',
            'work_order_id': wo.id,
            'book_no': wo.book.book_no,
            'detail': {
                'pressing_completed_at': wo.pressing_completed_at,
                'reviewer': wo.reviewer.get_full_name() if wo.reviewer else '',
                'days_passed': days_passed,
            }
        })

    completed_orders = WorkOrder.objects.filter(
        status=WorkOrder.STATUS_READY_STORAGE,
        started_at__isnull=False,
        completed_at__isnull=False
    ).select_related('restorer')

    all_days = []
    restorer_data = {}
    for wo in completed_orders:
        days = (wo.completed_at - wo.started_at).days
        all_days.append(days)
        rid = wo.restorer_id
        if rid not in restorer_data:
            restorer_data[rid] = {
                'name': wo.restorer.get_full_name(),
                'days_list': [],
                'order_count': 0,
            }
        restorer_data[rid]['days_list'].append(days)
        restorer_data[rid]['order_count'] += 1

    overall_avg_days = sum(all_days) / len(all_days) if all_days else 0

    for rid, data in restorer_data.items():
        if data['order_count'] >= 3 and overall_avg_days > 0:
            avg_days = sum(data['days_list']) / len(data['days_list'])
            deviation = (avg_days - overall_avg_days) / overall_avg_days
            if abs(deviation) >= 0.5:
                alerts.append({
                    'type': 'abnormal_cycle',
                    'level': 'info',
                    'message': f'责任人 {data["name"]} 处理周期异常',
                    'restorer_id': rid,
                    'detail': {
                        'restorer_name': data['name'],
                        'avg_days': round(avg_days, 1),
                        'overall_avg_days': round(overall_avg_days, 1),
                        'deviation_percent': round(deviation * 100, 1),
                        'order_count': data['order_count'],
                    }
                })

    return Response({
        'total': len(alerts),
        'alerts': alerts,
    })
