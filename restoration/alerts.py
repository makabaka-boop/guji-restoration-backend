from django.utils import timezone
from django.db.models import Count, Avg, F, ExpressionWrapper, fields as db_fields
from .models import WorkOrder, Alert, BookVolume


def check_review_overdue():
    now = timezone.now()
    orders = WorkOrder.objects.filter(
        status=WorkOrder.STATUS_PENDING_REVIEW,
        pressing_completed_at__isnull=False,
    ).select_related('book')
    for order in orders:
        interval_days = order.book.review_interval_days
        deadline = order.pressing_completed_at + timezone.timedelta(days=interval_days)
        if now > deadline:
            existing = Alert.objects.filter(
                work_order=order,
                alert_type='review_overdue',
                is_resolved=False,
            ).exists()
            if not existing:
                Alert.objects.create(
                    alert_type='review_overdue',
                    work_order=order,
                    message=f'书册 {order.book.code} 复核已超期，压平完成于 {order.pressing_completed_at.strftime("%Y-%m-%d")}，'
                            f'复核间隔 {interval_days} 天',
                )


def check_high_rework_by_paper_type():
    paper_types = BookVolume.objects.values_list('paper_type', flat=True).distinct()
    for paper_type in paper_types:
        book_ids = BookVolume.objects.filter(paper_type=paper_type).values_list('id', flat=True)
        total_count = WorkOrder.objects.filter(book__id__in=book_ids).count()
        rework_count = WorkOrder.objects.filter(
            book__id__in=book_ids, rework_count__gt=0
        ).count()
        if total_count >= 3 and rework_count / total_count > 0.5:
            existing = Alert.objects.filter(
                alert_type='high_rework',
                is_resolved=False,
                message__contains=paper_type,
            ).exists()
            if not existing:
                Alert.objects.create(
                    alert_type='high_rework',
                    message=f'纸张类型「{paper_type}」返工比例偏高：{rework_count}/{total_count}',
                )


def check_no_review_after_pressing():
    now = timezone.now()
    orders = WorkOrder.objects.filter(
        status=WorkOrder.STATUS_PENDING_REVIEW,
        pressing_completed_at__isnull=False,
    ).select_related('book')
    for order in orders:
        elapsed = (now - order.pressing_completed_at).total_seconds()
        if elapsed > 3 * 86400:
            existing = Alert.objects.filter(
                work_order=order,
                alert_type='no_review_after_pressing',
                is_resolved=False,
            ).exists()
            if not existing:
                Alert.objects.create(
                    alert_type='no_review_after_pressing',
                    work_order=order,
                    message=f'书册 {order.book.code} 压平完成后超过3天仍未复核',
                )


def check_abnormal_cycle():
    completed_orders = WorkOrder.objects.filter(
        status=WorkOrder.STATUS_CAN_STORE,
        operator__isnull=False,
    )
    if completed_orders.count() < 5:
        return
    avg_cycle = completed_orders.annotate(
        cycle=ExpressionWrapper(F('updated_at') - F('created_at'), output_field=db_fields.DurationField())
    ).aggregate(avg=Avg('cycle'))['avg']
    if avg_cycle is None:
        return
    threshold = avg_cycle * 2
    active_orders = WorkOrder.objects.filter(
        status__in=WorkOrder.ACTIVE_STATUSES,
        operator__isnull=False,
    ).select_related('book', 'operator')
    for order in active_orders:
        elapsed = now_or_zero(order)
        if elapsed and elapsed > threshold:
            existing = Alert.objects.filter(
                work_order=order,
                alert_type='abnormal_cycle',
                is_resolved=False,
            ).exists()
            if not existing:
                Alert.objects.create(
                    alert_type='abnormal_cycle',
                    work_order=order,
                    message=f'责任人 {order.operator.username} 处理书册 {order.book.code} 周期异常，'
                            f'已耗时 {(timezone.now() - order.created_at).days} 天，'
                            f'平均周期 {avg_cycle.days} 天',
                )


def now_or_zero(order):
    from django.utils import timezone as tz
    return tz.now() - order.created_at


def run_all_alerts():
    check_review_overdue()
    check_high_rework_by_paper_type()
    check_no_review_after_pressing()
    check_abnormal_cycle()
