from rest_framework import viewsets, status, permissions, serializers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Avg, Q, F, Case, When, IntegerField
from django.conf import settings
from datetime import timedelta

from .models import (
    User, PaperType, BindingType, WorkStation, ResponsiblePerson,
    Book, WorkOrder, RepairRecord, ReviewRecord
)
from .serializers import (
    UserSerializer, UserCreateSerializer,
    PaperTypeSerializer, BindingTypeSerializer, WorkStationSerializer,
    ResponsiblePersonSerializer, BookSerializer,
    WorkOrderListSerializer, WorkOrderDetailSerializer, WorkOrderCreateSerializer,
    RepairRecordSerializer, RepairSubmitSerializer,
    ReviewRecordSerializer, ReviewSubmitSerializer
)
from .permissions import (
    IsAdmin, IsRestorer, IsReviewer, IsAdminOrRestorer,
    IsAdminOrReviewer, IsAdminOrReadOnly
)
from .filters import WorkOrderFilter, BookFilter


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_info(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer


class PaperTypeViewSet(viewsets.ModelViewSet):
    queryset = PaperType.objects.all()
    serializer_class = PaperTypeSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None


class BindingTypeViewSet(viewsets.ModelViewSet):
    queryset = BindingType.objects.all()
    serializer_class = BindingTypeSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None


class WorkStationViewSet(viewsets.ModelViewSet):
    queryset = WorkStation.objects.all()
    serializer_class = WorkStationSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None


class ResponsiblePersonViewSet(viewsets.ModelViewSet):
    queryset = ResponsiblePerson.objects.all()
    serializer_class = ResponsiblePersonSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = BookFilter
    search_fields = ['book_no', 'title']
    ordering_fields = ['book_no', 'created_at']


class WorkOrderViewSet(viewsets.ModelViewSet):
    queryset = WorkOrder.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = WorkOrderFilter
    search_fields = ['order_no', 'book__book_no', 'book__title']
    ordering_fields = ['created_at', 'status', 'order_no']

    def get_serializer_class(self):
        if self.action == 'create':
            return WorkOrderCreateSerializer
        if self.action in ['retrieve', 'update', 'partial_update']:
            return WorkOrderDetailSerializer
        return WorkOrderListSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsAdmin]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdmin]
        else:
            action_method = getattr(self, self.action, None)
            if action_method and hasattr(action_method, 'kwargs') and 'permission_classes' in action_method.kwargs:
                permission_classes = action_method.kwargs['permission_classes']
            else:
                permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = serializer.validated_data.get('book')
        if book:
            active_orders = WorkOrder.objects.select_for_update().filter(
                book=book, status__in=WorkOrder.ACTIVE_STATUSES
            )
            if active_orders.exists():
                raise serializers.ValidationError({'book': ['该书册存在未结束的工单，无法创建新工单']})
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        detail_serializer = WorkOrderDetailSerializer(serializer.instance)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'], permission_classes=[IsRestorer])
    def receive(self, request, pk=None):
        order = self.get_object()
        if order.status != WorkOrder.STATUS_PENDING_RECEIVE:
            return Response({'detail': '工单状态不允许接收'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = WorkOrder.STATUS_PROCESSING
        order.receive_time = timezone.now()
        if not order.start_time:
            order.start_time = order.receive_time
        order.save()
        return Response(WorkOrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'], permission_classes=[IsRestorer])
    def start_process(self, request, pk=None):
        order = self.get_object()
        if order.status not in [WorkOrder.STATUS_PENDING_RECEIVE, WorkOrder.STATUS_PAUSED, WorkOrder.STATUS_REWORKING]:
            return Response({'detail': '工单状态不允许开始处理'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = WorkOrder.STATUS_PROCESSING
        if not order.start_time:
            order.start_time = timezone.now()
        order.save()
        return Response(WorkOrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'], permission_classes=[IsRestorer])
    def submit_repair(self, request, pk=None):
        order = self.get_object()
        if order.status not in [WorkOrder.STATUS_PROCESSING, WorkOrder.STATUS_REWORKING]:
            return Response({'detail': '工单状态不允许提交修护'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = RepairSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        RepairRecord.objects.create(
            work_order=order,
            restorer=request.user,
            has_page_separation=data.get('has_page_separation', False),
            has_paper_repair=data.get('has_paper_repair', False),
            has_pressing=data.get('has_pressing', False),
            has_binding=data.get('has_binding', False),
            damage_description=data.get('damage_description'),
            process_remark=data.get('process_remark')
        )

        if data.get('damage_description'):
            order.damage_description = data['damage_description']
        if data.get('process_remark'):
            order.process_remark = data['process_remark']

        if data.get('has_pressing', False):
            order.status = WorkOrder.STATUS_PENDING_PRESS
            order.press_start_time = timezone.now()

        order.save()
        return Response(WorkOrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'], permission_classes=[IsRestorer])
    def complete_pressing(self, request, pk=None):
        order = self.get_object()
        if order.status != WorkOrder.STATUS_PENDING_PRESS:
            return Response({'detail': '工单状态不允许完成压平'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = WorkOrder.STATUS_PENDING_REVIEW
        order.press_complete_time = timezone.now()
        order.review_submit_time = timezone.now()
        order.save()
        return Response(WorkOrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'], permission_classes=[IsRestorer])
    def submit_for_review(self, request, pk=None):
        order = self.get_object()
        if order.status not in [WorkOrder.STATUS_PROCESSING, WorkOrder.STATUS_REWORKING]:
            return Response({'detail': '工单状态不允许提交复核'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = WorkOrder.STATUS_PENDING_REVIEW
        order.review_submit_time = timezone.now()
        order.save()
        return Response(WorkOrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'], permission_classes=[IsReviewer])
    def submit_review(self, request, pk=None):
        order = self.get_object()
        if order.status != WorkOrder.STATUS_PENDING_REVIEW:
            return Response({'detail': '工单状态不允许复核'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReviewSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        ReviewRecord.objects.create(
            work_order=order,
            reviewer=request.user,
            flatness=data['flatness'],
            page_order=data['page_order'],
            cover_status=data['cover_status'],
            conclusion=data['conclusion'],
            rework_reason=data.get('rework_reason'),
            review_remark=data.get('review_remark')
        )

        if data['conclusion'] == ReviewRecord.RESULT_PASS:
            order.status = WorkOrder.STATUS_STORABLE
            order.complete_time = timezone.now()
        elif data['conclusion'] == ReviewRecord.RESULT_REWORK:
            order.status = WorkOrder.STATUS_REWORKING
            order.rework_count = F('rework_count') + 1
        elif data['conclusion'] == ReviewRecord.RESULT_PENDING:
            order.status = WorkOrder.STATUS_PROCESSING

        if not order.reviewer:
            order.reviewer = request.user

        order.save()
        order.refresh_from_db()
        return Response(WorkOrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def pause(self, request, pk=None):
        order = self.get_object()
        if order.status in [WorkOrder.STATUS_STORABLE, WorkOrder.STATUS_PAUSED]:
            return Response({'detail': '工单状态不允许暂停'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = WorkOrder.STATUS_PAUSED
        order.save()
        return Response(WorkOrderDetailSerializer(order).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def resume(self, request, pk=None):
        order = self.get_object()
        if order.status != WorkOrder.STATUS_PAUSED:
            return Response({'detail': '工单状态不允许恢复'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = WorkOrder.STATUS_PROCESSING
        order.save()
        return Response(WorkOrderDetailSerializer(order).data)

    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        user = request.user
        if user.role == User.ROLE_RESTORER:
            qs = self.queryset.filter(restorer=user).filter(
                status__in=WorkOrder.ACTIVE_STATUSES
            )
        elif user.role == User.ROLE_REVIEWER:
            qs = self.queryset.filter(
                status=WorkOrder.STATUS_PENDING_REVIEW
            )
        else:
            qs = self.queryset.all()

        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class StatisticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        result = {}
        result['rework_reason_distribution'] = self._get_rework_reason_distribution()
        result['pending_review_books'] = self._get_pending_review_books()
        result['process_cycle_distribution'] = self._get_process_cycle_distribution()
        return Response(result)

    def _get_rework_reason_distribution(self):
        rework_records = ReviewRecord.objects.filter(conclusion=ReviewRecord.RESULT_REWORK)
        reasons = rework_records.values_list('rework_reason', flat=True)
        reason_map = {}
        for reason in reasons:
            if not reason:
                reason = '未填写原因'
            reason_map[reason] = reason_map.get(reason, 0) + 1

        result = [
            {'reason': k, 'count': v}
            for k, v in sorted(reason_map.items(), key=lambda x: x[1], reverse=True)
        ]
        return result[:10]

    def _get_pending_review_books(self):
        pending_orders = WorkOrder.objects.filter(
            status=WorkOrder.STATUS_PENDING_REVIEW
        ).select_related('book', 'work_station', 'responsible_person')

        return WorkOrderListSerializer(pending_orders, many=True).data

    def _get_process_cycle_distribution(self):
        completed_orders = WorkOrder.objects.filter(
            status=WorkOrder.STATUS_STORABLE,
            start_time__isnull=False,
            complete_time__isnull=False
        )

        cycles = []
        for order in completed_orders:
            if order.start_time and order.complete_time:
                hours = (order.complete_time - order.start_time).total_seconds() / 3600
                cycles.append(hours)

        if not cycles:
            return {
                'average_hours': 0,
                'min_hours': 0,
                'max_hours': 0,
                'total_count': 0,
                'distribution': []
            }

        intervals = [
            (0, 24, '0-24小时'),
            (24, 48, '24-48小时'),
            (48, 72, '48-72小时'),
            (72, 168, '3-7天'),
            (168, 720, '7-30天'),
            (720, float('inf'), '30天以上'),
        ]

        distribution = []
        for start, end, label in intervals:
            count = sum(1 for c in cycles if start <= c < end)
            distribution.append({'range': label, 'count': count})

        return {
            'average_hours': round(sum(cycles) / len(cycles), 2),
            'min_hours': round(min(cycles), 2),
            'max_hours': round(max(cycles), 2),
            'total_count': len(cycles),
            'distribution': distribution
        }


class AlertView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        alerts = []
        alerts.extend(self._get_overdue_review_alerts())
        alerts.extend(self._get_high_rework_rate_alerts())
        alerts.extend(self._get_press_no_review_alerts())
        alerts.extend(self._get_abnormal_cycle_alerts())
        return Response({'alerts': alerts, 'total': len(alerts)})

    def _get_overdue_review_alerts(self):
        from django.db.models import F, ExpressionWrapper, fields
        now = timezone.now()

        pending_orders = WorkOrder.objects.filter(
            status=WorkOrder.STATUS_PENDING_REVIEW,
            review_submit_time__isnull=False
        ).select_related('book')

        alerts = []
        for order in pending_orders:
            interval_hours = order.review_interval_hours or 24
            threshold_time = now - timedelta(hours=interval_hours)
            if order.review_submit_time <= threshold_time:
                overdue_hours = round(
                    (now - order.review_submit_time).total_seconds() / 3600, 1
                )
                alerts.append({
                    'type': 'overdue_review',
                    'type_name': '复核超期',
                    'level': 'warning',
                    'order_no': order.order_no,
                    'book_no': order.book.book_no,
                    'message': f'工单 {order.order_no} 已超期 {overdue_hours} 小时未复核（设定间隔{interval_hours}小时）',
                    'review_interval_hours': interval_hours,
                    'overdue_hours': overdue_hours,
                    'review_submit_time': order.review_submit_time
                })
        return alerts

    def _get_high_rework_rate_alerts(self):
        from django.conf import settings
        threshold = getattr(settings, 'REWORK_RATE_THRESHOLD', 0.3)

        paper_types = PaperType.objects.all()
        alerts = []

        for pt in paper_types:
            total_orders = WorkOrder.objects.filter(
                book__paper_type=pt
            ).count()
            if total_orders < 3:
                continue

            rework_count = WorkOrder.objects.filter(
                book__paper_type=pt,
                rework_count__gt=0
            ).count()

            rework_rate = rework_count / total_orders if total_orders > 0 else 0

            if rework_rate >= threshold:
                alerts.append({
                    'type': 'high_rework_rate',
                    'type_name': '返工率偏高',
                    'level': 'warning',
                    'paper_type_id': pt.id,
                    'paper_type_name': pt.name,
                    'message': f'纸张类型「{pt.name}」返工率达 {rework_rate*100:.1f}%',
                    'rework_rate': round(rework_rate, 4),
                    'total_count': total_orders,
                    'rework_count': rework_count
                })
        return alerts

    def _get_press_no_review_alerts(self):
        orders = WorkOrder.objects.filter(
            status=WorkOrder.STATUS_PENDING_PRESS,
            press_complete_time__isnull=False
        ).select_related('book')

        alerts = []
        for order in orders:
            hours_since_press = round(
                (timezone.now() - order.press_complete_time).total_seconds() / 3600, 1
            ) if order.press_complete_time else 0
            alerts.append({
                'type': 'press_no_review',
                'type_name': '压平完成未复核',
                'level': 'info',
                'order_no': order.order_no,
                'book_no': order.book.book_no,
                'message': f'工单 {order.order_no} 压平已完成 {hours_since_press} 小时，尚未提交复核',
                'press_complete_time': order.press_complete_time
            })
        return alerts

    def _get_abnormal_cycle_alerts(self):
        from django.conf import settings
        cycle_days = getattr(settings, 'PROCESS_CYCLE_DAYS', 7)
        threshold_hours = cycle_days * 24

        avg_cycles = WorkOrder.objects.filter(
            status=WorkOrder.STATUS_STORABLE,
            start_time__isnull=False,
            complete_time__isnull=False
        ).values('responsible_person').annotate(
            avg_hours=Avg(F('complete_time') - F('start_time'))
        )

        alerts = []
        overall_avg = None
        completed_orders = WorkOrder.objects.filter(
            status=WorkOrder.STATUS_STORABLE,
            start_time__isnull=False,
            complete_time__isnull=False
        )
        if completed_orders.exists():
            total_seconds = sum(
                (o.complete_time - o.start_time).total_seconds()
                for o in completed_orders
            )
            overall_avg = total_seconds / len(completed_orders) / 3600

        for item in avg_cycles:
            avg_hours = item['avg_hours'].total_seconds() / 3600 if item['avg_hours'] else 0
            if overall_avg and avg_hours > overall_avg * 1.5 and avg_hours > threshold_hours:
                try:
                    person = ResponsiblePerson.objects.get(id=item['responsible_person'])
                    alerts.append({
                        'type': 'abnormal_cycle',
                        'type_name': '处理周期异常',
                        'level': 'info',
                        'responsible_person_id': person.id,
                        'responsible_person_name': person.name,
                        'message': f'责任人 {person.name} 平均处理周期 {avg_hours:.1f} 小时，高于平均值',
                        'avg_hours': round(avg_hours, 2),
                        'overall_avg_hours': round(overall_avg, 2)
                    })
                except ResponsiblePerson.DoesNotExist:
                    pass
        return alerts
