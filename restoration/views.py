from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import (
    User, PaperType, BindingType, Station, Book, WorkOrder,
    RestorationRecord, ReviewRecord, StatusLog,
    ROLE_ADMIN, ROLE_RESTORER, ROLE_REVIEWER,
    STATUS_PENDING, STATUS_PROCESSING, STATUS_PENDING_PRESS,
    STATUS_PENDING_REVIEW, STATUS_REWORKING, STATUS_STORABLE, STATUS_PAUSED,
    REVIEW_PASS, REVIEW_REWORK,
)
from .serializers import (
    UserSerializer, UserCreateSerializer,
    PaperTypeSerializer, BindingTypeSerializer, StationSerializer,
    BookSerializer, BookListSerializer,
    WorkOrderSerializer, WorkOrderCreateSerializer, WorkOrderListSerializer,
    RestorationRecordSerializer, ReviewRecordSerializer,
    RestorationSubmitSerializer, ReviewSubmitSerializer, PauseSerializer,
    StatusLogSerializer,
)
from .permissions import (
    IsAdmin, IsRestorer, IsReviewer,
    IsAdminOrRestorer, IsAdminOrReviewer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        user = User.objects.get(username=request.data.get('username'))
        response.data['user'] = UserSerializer(user).data
        return response


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        keyword = self.request.query_params.get('keyword')
        if keyword:
            qs = qs.filter(
                Q(username__icontains=keyword) |
                Q(first_name__icontains=keyword) |
                Q(last_name__icontains=keyword)
            )
        return qs


class PaperTypeViewSet(viewsets.ModelViewSet):
    queryset = PaperType.objects.all().order_by('-created_at')
    serializer_class = PaperTypeSerializer
    permission_classes = [IsAdmin]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [IsAdmin()]


class BindingTypeViewSet(viewsets.ModelViewSet):
    queryset = BindingType.objects.all().order_by('-created_at')
    serializer_class = BindingTypeSerializer
    permission_classes = [IsAdmin]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [IsAdmin()]


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all().order_by('-created_at')
    serializer_class = StationSerializer
    permission_classes = [IsAdmin]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [IsAdmin()]


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all().order_by('-created_at')
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.action == 'list':
            return BookListSerializer
        return BookSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [IsAdmin()]

    def get_queryset(self):
        qs = super().get_queryset()
        book_number = self.request.query_params.get('book_number')
        if book_number:
            qs = qs.filter(book_number__icontains=book_number)
        paper_type = self.request.query_params.get('paper_type')
        if paper_type:
            qs = qs.filter(paper_type_id=paper_type)
        binding_type = self.request.query_params.get('binding_type')
        if binding_type:
            qs = qs.filter(binding_type_id=binding_type)
        restorer = self.request.query_params.get('restorer')
        if restorer:
            qs = qs.filter(default_restorer_id=restorer)
        has_active = self.request.query_params.get('has_active_order')
        if has_active == 'true':
            active_ids = WorkOrder.objects.exclude(status=STATUS_STORABLE).values_list('book_id', flat=True)
            qs = qs.filter(id__in=active_ids)
        elif has_active == 'false':
            active_ids = WorkOrder.objects.exclude(status=STATUS_STORABLE).values_list('book_id', flat=True)
            qs = qs.exclude(id__in=active_ids)
        return qs


class WorkOrderViewSet(viewsets.ModelViewSet):
    queryset = WorkOrder.objects.all().order_by('-created_at')
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return WorkOrderCreateSerializer
        if self.action == 'list':
            return WorkOrderListSerializer
        return WorkOrderSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        book_number = self.request.query_params.get('book_number')
        if book_number:
            qs = qs.filter(book__book_number__icontains=book_number)
        paper_type = self.request.query_params.get('paper_type')
        if paper_type:
            qs = qs.filter(book__paper_type_id=paper_type)
        station = self.request.query_params.get('station')
        if station:
            qs = qs.filter(station_id=station)
        status_ = self.request.query_params.get('status')
        if status_:
            qs = qs.filter(status=status_)
        restorer = self.request.query_params.get('restorer')
        if restorer:
            qs = qs.filter(restorer_id=restorer)
        start_date = self.request.query_params.get('start_date')
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        end_date = self.request.query_params.get('end_date')
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)
        if self.request.user.role == ROLE_RESTORER:
            qs = qs.filter(restorer=self.request.user)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = serializer.validated_data['book']
        station = serializer.validated_data['station']
        restorer = serializer.validated_data['restorer']
        review_interval = serializer.validated_data.get(
            'review_interval_days', book.review_interval_days
        )

        order = WorkOrder(
            book=book, station=station, restorer=restorer,
            review_interval_days=review_interval,
            status=STATUS_PENDING,
        )
        order.save()

        StatusLog.objects.create(
            work_order=order, to_status=STATUS_PENDING,
            operator=request.user, remark='工单创建',
        )

        output = WorkOrderSerializer(order)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def receive(self, request, pk=None):
        if request.user.role != ROLE_RESTORER:
            return Response({'error': '只有修护师可以接收工单'}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        if order.status not in [STATUS_PENDING, STATUS_REWORKING]:
            return Response({'error': '当前状态不可接收'}, status=status.HTTP_400_BAD_REQUEST)
        if order.restorer_id != request.user.id:
            return Response({'error': '只能接收分配给自己的工单'}, status=status.HTTP_403_FORBIDDEN)

        old_status = order.status
        order.status = STATUS_PROCESSING
        if not order.received_at:
            order.received_at = timezone.now()
        order.processing_started_at = timezone.now()
        order.save()

        StatusLog.objects.create(
            work_order=order, from_status=old_status,
            to_status=STATUS_PROCESSING, operator=request.user,
            remark='接收工单，开始处理',
        )
        return Response(WorkOrderSerializer(order).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def submit_restoration(self, request, pk=None):
        if request.user.role != ROLE_RESTORER:
            return Response({'error': '只有修护师可以提交修护记录'}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        if order.status not in [STATUS_PROCESSING, STATUS_REWORKING]:
            return Response({'error': '当前状态不可提交修护记录'}, status=status.HTTP_400_BAD_REQUEST)
        if order.restorer_id != request.user.id:
            return Response({'error': '只能处理分配给自己的工单'}, status=status.HTTP_403_FORBIDDEN)

        serializer = RestorationSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        record = RestorationRecord.objects.create(
            work_order=order, restorer=request.user,
            disassembly_done=data.get('disassembly_done', False),
            disassembly_note=data.get('disassembly_note', ''),
            paper_repair_done=data.get('paper_repair_done', False),
            paper_repair_note=data.get('paper_repair_note', ''),
            press_done=data.get('press_done', False),
            press_level=data.get('press_level', ''),
            press_duration_hours=data.get('press_duration_hours'),
            press_note=data.get('press_note', ''),
            binding_done=data.get('binding_done', False),
            binding_note=data.get('binding_note', ''),
            damage_description=data.get('damage_description', ''),
            handling_note=data.get('handling_note', ''),
        )

        old_status = order.status
        if data.get('press_done') and data.get('binding_done'):
            order.status = STATUS_PENDING_REVIEW
            order.press_completed_at = timezone.now()
            if not order.press_started_at:
                order.press_started_at = timezone.now()
            order.review_due_at = timezone.now() + timezone.timedelta(days=order.review_interval_days)
            remark = '修护完成，提交复核'
        elif data.get('press_done'):
            order.status = STATUS_PENDING_PRESS
            order.press_completed_at = timezone.now()
            if not order.press_started_at:
                order.press_started_at = timezone.now()
            remark = '压平完成，等待装订'
        else:
            remark = '提交修护记录'

        order.save()

        if old_status != order.status:
            StatusLog.objects.create(
                work_order=order, from_status=old_status,
                to_status=order.status, operator=request.user,
                remark=remark,
            )

        return Response(WorkOrderSerializer(order).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def pause(self, request, pk=None):
        if request.user.role != ROLE_RESTORER:
            return Response({'error': '只有修护师可以暂停工单'}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        if order.status in [STATUS_STORABLE, STATUS_PAUSED]:
            return Response({'error': '当前状态不可暂停'}, status=status.HTTP_400_BAD_REQUEST)
        if order.restorer_id != request.user.id:
            return Response({'error': '只能暂停分配给自己的工单'}, status=status.HTTP_403_FORBIDDEN)

        serializer = PauseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data['reason']

        old_status = order.status
        order.status = STATUS_PAUSED
        order.pause_reason = reason
        order.save()

        StatusLog.objects.create(
            work_order=order, from_status=old_status,
            to_status=STATUS_PAUSED, operator=request.user,
            remark=f'暂停: {reason}',
        )
        return Response(WorkOrderSerializer(order).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def resume(self, request, pk=None):
        if request.user.role != ROLE_RESTORER:
            return Response({'error': '只有修护师可以恢复工单'}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        if order.status != STATUS_PAUSED:
            return Response({'error': '当前状态不可恢复'}, status=status.HTTP_400_BAD_REQUEST)
        if order.restorer_id != request.user.id:
            return Response({'error': '只能恢复分配给自己的工单'}, status=status.HTTP_403_FORBIDDEN)

        old_status = order.status
        target = STATUS_PROCESSING if order.rework_count > 0 and order.review_completed_at else STATUS_PROCESSING
        if order.restoration_records.filter(press_done=True).exists() and not order.review_records.exists():
            target = STATUS_PENDING_PRESS
        order.status = target
        order.pause_reason = ''
        order.save()

        StatusLog.objects.create(
            work_order=order, from_status=old_status,
            to_status=target, operator=request.user,
            remark='恢复处理',
        )
        return Response(WorkOrderSerializer(order).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def submit_review(self, request, pk=None):
        if request.user.role != ROLE_REVIEWER:
            return Response({'error': '只有复核员可以提交复核记录'}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        if order.status != STATUS_PENDING_REVIEW:
            return Response({'error': '当前状态不可提交复核'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReviewSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        conclusion = data['conclusion']
        record = ReviewRecord.objects.create(
            work_order=order, reviewer=request.user,
            flatness=data['flatness'],
            flatness_note=data.get('flatness_note', ''),
            page_order_correct=data.get('page_order_correct', True),
            page_order_note=data.get('page_order_note', ''),
            cover_status=data['cover_status'],
            cover_note=data.get('cover_note', ''),
            conclusion=conclusion,
            rework_reason=data.get('rework_reason', ''),
            review_note=data.get('review_note', ''),
        )

        old_status = order.status
        order.review_completed_at = timezone.now()
        if conclusion == REVIEW_PASS:
            order.status = STATUS_STORABLE
            order.completed_at = timezone.now()
            remark = '复核通过，可入库'
        else:
            order.status = STATUS_REWORKING
            order.rework_count = F('rework_count') + 1
            remark = f'复核不通过，返工原因: {data.get("rework_reason", "")}'

        order.save()

        StatusLog.objects.create(
            work_order=order, from_status=old_status,
            to_status=order.status, operator=request.user,
            remark=remark,
        )

        return Response(WorkOrderSerializer(order).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def mark_stored(self, request, pk=None):
        order = self.get_object()
        if order.status != STATUS_STORABLE:
            return Response({'error': '只有可入库状态的工单才能标记已入库'}, status=status.HTTP_400_BAD_REQUEST)
        old_status = order.status
        order.status = STATUS_STORABLE
        order.completed_at = timezone.now()
        order.save()
        StatusLog.objects.create(
            work_order=order, from_status=old_status,
            to_status=STATUS_STORABLE, operator=request.user,
            remark='已入库归档',
        )
        return Response(WorkOrderSerializer(order).data)

    @action(detail=True, methods=['get'])
    def status_logs(self, request, pk=None):
        order = self.get_object()
        logs = order.status_logs.all()
        return Response(StatusLogSerializer(logs, many=True).data)


class StatisticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        rework_qs = ReviewRecord.objects.filter(conclusion=REVIEW_REWORK)
        rework_reasons = rework_qs.values('rework_reason').annotate(
            count=Count('id')
        ).order_by('-count')
        rework_list = [
            {'reason': item['rework_reason'] or '未填写', 'count': item['count']}
            for item in rework_reasons
        ]

        pending_review = WorkOrder.objects.filter(status=STATUS_PENDING_REVIEW).count()

        completed_orders = WorkOrder.objects.filter(status=STATUS_STORABLE)
        cycle_data = []
        ranges = [
            (0, 24, '0-24小时'),
            (24, 72, '24-72小时'),
            (72, 168, '72-168小时'),
            (168, 720, '168-720小时'),
            (720, float('inf'), '720小时以上'),
        ]
        for low, high, label in ranges:
            count = 0
            for order in completed_orders:
                hours = order.processing_cycle_hours
                if low <= hours < high:
                    count += 1
            cycle_data.append({'range': label, 'count': count})

        avg_cycle = 0
        if completed_orders.exists():
            total = 0
            cnt = 0
            for o in completed_orders:
                h = o.processing_cycle_hours
                if h > 0:
                    total += h
                    cnt += 1
            if cnt:
                avg_cycle = round(total / cnt, 2)

        data = {
            'rework_reason_distribution': rework_list,
            'pending_review_books': pending_review,
            'processing_cycle_ranges': cycle_data,
            'avg_processing_cycle_hours': avg_cycle,
            'total_orders': WorkOrder.objects.count(),
            'completed_orders': completed_orders.count(),
            'in_progress_orders': WorkOrder.objects.exclude(
                status__in=[STATUS_STORABLE, STATUS_PENDING]
            ).count(),
        }
        return Response(data)


class AnomalyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        review_overdue_qs = WorkOrder.objects.filter(
            status=STATUS_PENDING_REVIEW, review_due_at__lt=now
        ).select_related('book', 'restorer')
        review_overdue = [
            {
                'order_no': o.order_no,
                'book_number': o.book.book_number,
                'restorer': o.restorer.username,
                'review_due_at': o.review_due_at,
                'overdue_hours': round((now - o.review_due_at).total_seconds() / 3600, 2),
            }
            for o in review_overdue_qs
        ]

        rework_by_paper = WorkOrder.objects.filter(
            rework_count__gt=0
        ).values('book__paper_type__name').annotate(
            total=Count('id'),
            rework_count=Count('rework_count'),
        ).order_by('-rework_count')
        high_rework_paper = [
            {
                'paper_type': item['book__paper_type__name'],
                'total_orders': item['total'],
                'rework_count': item['rework_count'],
                'rework_rate': round(item['rework_count'] / item['total'] * 100, 2) if item['total'] else 0,
            }
            for item in rework_by_paper if item['rework_count'] >= 2
        ]

        no_review_after_press = []
        press_orders = WorkOrder.objects.filter(
            press_completed_at__isnull=False,
            status__in=[STATUS_PENDING_PRESS, STATUS_PROCESSING]
        ).select_related('book', 'restorer')
        for o in press_orders:
            if o.press_completed_at and (now - o.press_completed_at).total_seconds() > 86400 * 3:
                no_review_after_press.append({
                    'order_no': o.order_no,
                    'book_number': o.book.book_number,
                    'restorer': o.restorer.username,
                    'press_completed_at': o.press_completed_at,
                    'status': o.get_status_display(),
                    'days_since_press': round((now - o.press_completed_at).total_seconds() / 86400, 2),
                })

        completed_orders = WorkOrder.objects.filter(status=STATUS_STORABLE).select_related('restorer')
        restorer_cycles = {}
        for o in completed_orders:
            rid = o.restorer_id
            h = o.processing_cycle_hours
            if h > 0:
                if rid not in restorer_cycles:
                    restorer_cycles[rid] = {'name': o.restorer.username, 'hours': [], 'count': 0}
                restorer_cycles[rid]['hours'].append(h)
                restorer_cycles[rid]['count'] += 1

        all_avg = 0
        all_hours = []
        for data in restorer_cycles.values():
            all_hours.extend(data['hours'])
        if all_hours:
            all_avg = sum(all_hours) / len(all_hours)

        abnormal_cycle = []
        for rid, data in restorer_cycles.items():
            if data['count'] >= 2 and all_avg > 0:
                avg = sum(data['hours']) / len(data['hours'])
                diff_ratio = abs(avg - all_avg) / all_avg
                if diff_ratio > 0.5:
                    abnormal_cycle.append({
                        'restorer': data['name'],
                        'avg_hours': round(avg, 2),
                        'overall_avg_hours': round(all_avg, 2),
                        'deviation_percent': round(diff_ratio * 100, 2),
                        'order_count': data['count'],
                    })

        data = {
            'review_overdue': review_overdue,
            'high_rework_by_paper': high_rework_paper,
            'no_review_after_press': no_review_after_press,
            'abnormal_cycle': abnormal_cycle,
        }
        return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user(request):
    return Response(UserSerializer(request.user).data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_summary(request):
    now = timezone.now()
    data = {
        'total_books': Book.objects.count(),
        'active_orders': WorkOrder.objects.exclude(status=STATUS_STORABLE).count(),
        'pending_review': WorkOrder.objects.filter(status=STATUS_PENDING_REVIEW).count(),
        'in_processing': WorkOrder.objects.filter(
            status__in=[STATUS_PROCESSING, STATUS_REWORKING, STATUS_PENDING_PRESS]
        ).count(),
        'completed_today': WorkOrder.objects.filter(
            status=STATUS_STORABLE, completed_at__date=now.date()
        ).count(),
        'review_overdue': WorkOrder.objects.filter(
            status=STATUS_PENDING_REVIEW, review_due_at__lt=now
        ).count(),
    }
    return Response(data)
