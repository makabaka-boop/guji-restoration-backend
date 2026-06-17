from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


ROLE_ADMIN = 'admin'
ROLE_RESTORER = 'restorer'
ROLE_REVIEWER = 'reviewer'
ROLE_CHOICES = [
    (ROLE_ADMIN, '管理员'),
    (ROLE_RESTORER, '修护师'),
    (ROLE_REVIEWER, '复核员'),
]

STATUS_PENDING = 'pending'
STATUS_PROCESSING = 'processing'
STATUS_PENDING_PRESS = 'pending_press'
STATUS_PENDING_REVIEW = 'pending_review'
STATUS_REWORKING = 'reworking'
STATUS_STORABLE = 'storable'
STATUS_PAUSED = 'paused'
STATUS_CHOICES = [
    (STATUS_PENDING, '待接收'),
    (STATUS_PROCESSING, '处理中'),
    (STATUS_PENDING_PRESS, '待压平'),
    (STATUS_PENDING_REVIEW, '待复核'),
    (STATUS_REWORKING, '返工中'),
    (STATUS_STORABLE, '可入库'),
    (STATUS_PAUSED, '暂停处理'),
]

REVIEW_PASS = 'pass'
REVIEW_REWORK = 'rework'
REVIEW_CONCLUSION_CHOICES = [
    (REVIEW_PASS, '通过'),
    (REVIEW_REWORK, '返工'),
]

PRESSURE_LEVEL_CHOICES = [
    ('light', '轻度'),
    ('medium', '中度'),
    ('heavy', '重度'),
]

FLATNESS_CHOICES = [
    ('excellent', '优秀'),
    ('good', '良好'),
    ('fair', '一般'),
    ('poor', '较差'),
]

COVER_STATUS_CHOICES = [
    ('intact', '完好'),
    ('minor_damage', '轻微破损'),
    ('major_damage', '严重破损'),
]


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_RESTORER, verbose_name='角色')
    phone = models.CharField(max_length=20, blank=True, verbose_name='电话')

    class Meta:
        db_table = 'user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


class PaperType(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='纸张类型')
    description = models.TextField(blank=True, verbose_name='说明')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'paper_type'
        verbose_name = '纸张类型'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class BindingType(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='装订形式')
    description = models.TextField(blank=True, verbose_name='说明')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'binding_type'
        verbose_name = '装订形式'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Station(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='台位名称')
    description = models.TextField(blank=True, verbose_name='说明')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'station'
        verbose_name = '处理台位'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Book(models.Model):
    book_number = models.CharField(max_length=50, unique=True, verbose_name='书册编号')
    paper_type = models.ForeignKey(PaperType, on_delete=models.PROTECT, verbose_name='纸张类型')
    binding_type = models.ForeignKey(BindingType, on_delete=models.PROTECT, verbose_name='装订形式')
    default_station = models.ForeignKey(Station, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='默认台位')
    default_restorer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_books', verbose_name='默认责任人'
    )
    review_interval_days = models.IntegerField(default=7, verbose_name='复核间隔(天)')
    description = models.TextField(blank=True, verbose_name='书册描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'book'
        verbose_name = '书册'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.book_number

    @property
    def active_work_order(self):
        return self.workorder_set.exclude(status__in=[STATUS_STORABLE]).first()


class WorkOrder(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='书册')
    order_no = models.CharField(max_length=50, unique=True, verbose_name='工单编号')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name='状态')
    station = models.ForeignKey(Station, on_delete=models.PROTECT, verbose_name='处理台位')
    restorer = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='restoration_orders',
        verbose_name='责任人(修护师)'
    )
    review_interval_days = models.IntegerField(default=7, verbose_name='复核间隔(天)')
    received_at = models.DateTimeField(null=True, blank=True, verbose_name='接收时间')
    processing_started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始处理时间')
    press_started_at = models.DateTimeField(null=True, blank=True, verbose_name='压平开始时间')
    press_completed_at = models.DateTimeField(null=True, blank=True, verbose_name='压平完成时间')
    review_due_at = models.DateTimeField(null=True, blank=True, verbose_name='复核到期时间')
    review_completed_at = models.DateTimeField(null=True, blank=True, verbose_name='复核完成时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    rework_count = models.IntegerField(default=0, verbose_name='返工次数')
    pause_reason = models.TextField(blank=True, verbose_name='暂停原因')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'work_order'
        verbose_name = '工单'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order_no} - {self.book.book_number}'

    def save(self, *args, **kwargs):
        if not self.order_no:
            self.order_no = f'WO{timezone.now().strftime("%Y%m%d%H%M%S")}'
        super().save(*args, **kwargs)

    @property
    def processing_cycle_hours(self):
        if self.received_at and self.completed_at:
            delta = self.completed_at - self.received_at
            return round(delta.total_seconds() / 3600, 2)
        if self.received_at:
            delta = timezone.now() - self.received_at
            return round(delta.total_seconds() / 3600, 2)
        return 0

    @property
    def is_review_overdue(self):
        if self.status == STATUS_PENDING_REVIEW and self.review_due_at:
            return timezone.now() > self.review_due_at
        return False


class RestorationRecord(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name='restoration_records', verbose_name='工单')
    restorer = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='修护师')
    disassembly_done = models.BooleanField(default=False, verbose_name='拆页完成')
    disassembly_note = models.TextField(blank=True, verbose_name='拆页说明')
    paper_repair_done = models.BooleanField(default=False, verbose_name='补纸完成')
    paper_repair_note = models.TextField(blank=True, verbose_name='补纸说明')
    press_done = models.BooleanField(default=False, verbose_name='压平完成')
    press_level = models.CharField(max_length=20, choices=PRESSURE_LEVEL_CHOICES, blank=True, verbose_name='压平程度')
    press_duration_hours = models.FloatField(null=True, blank=True, verbose_name='压平时长(小时)')
    press_note = models.TextField(blank=True, verbose_name='压平说明')
    binding_done = models.BooleanField(default=False, verbose_name='装订完成')
    binding_note = models.TextField(blank=True, verbose_name='装订说明')
    damage_description = models.TextField(blank=True, verbose_name='破损说明')
    handling_note = models.TextField(blank=True, verbose_name='处理备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='记录时间')

    class Meta:
        db_table = 'restoration_record'
        verbose_name = '修护记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.work_order.order_no} - 修护记录'


class ReviewRecord(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name='review_records', verbose_name='工单')
    reviewer = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='复核员')
    flatness = models.CharField(max_length=20, choices=FLATNESS_CHOICES, verbose_name='平整度')
    flatness_note = models.TextField(blank=True, verbose_name='平整度说明')
    page_order_correct = models.BooleanField(default=True, verbose_name='页序核对正确')
    page_order_note = models.TextField(blank=True, verbose_name='页序说明')
    cover_status = models.CharField(max_length=20, choices=COVER_STATUS_CHOICES, verbose_name='封面状态')
    cover_note = models.TextField(blank=True, verbose_name='封面说明')
    conclusion = models.CharField(max_length=20, choices=REVIEW_CONCLUSION_CHOICES, verbose_name='最终结论')
    rework_reason = models.TextField(blank=True, verbose_name='返工原因')
    review_note = models.TextField(blank=True, verbose_name='复核备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='复核时间')

    class Meta:
        db_table = 'review_record'
        verbose_name = '复核记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.work_order.order_no} - 复核记录'


class StatusLog(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name='status_logs', verbose_name='工单')
    from_status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, verbose_name='原状态')
    to_status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='新状态')
    operator = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='操作人')
    remark = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')

    class Meta:
        db_table = 'status_log'
        verbose_name = '状态日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.work_order.order_no}: {self.from_status} -> {self.to_status}'
