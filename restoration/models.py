from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError


class User(AbstractUser):
    ROLE_ADMIN = 'admin'
    ROLE_RESTORER = 'restorer'
    ROLE_REVIEWER = 'reviewer'

    ROLE_CHOICES = [
        (ROLE_ADMIN, '管理员'),
        (ROLE_RESTORER, '修护师'),
        (ROLE_REVIEWER, '复核员'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_RESTORER, verbose_name='角色')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='联系电话')

    class Meta:
        db_table = 'sys_user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


class PaperType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='纸张类型名称')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'paper_type'
        verbose_name = '纸张类型'
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        return self.name


class BindingType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='装订形式名称')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'binding_type'
        verbose_name = '装订形式'
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        return self.name


class WorkStation(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name='台位编号')
    name = models.CharField(max_length=100, verbose_name='台位名称')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'work_station'
        verbose_name = '处理台位'
        verbose_name_plural = verbose_name
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class ResponsiblePerson(models.Model):
    name = models.CharField(max_length=100, verbose_name='姓名')
    employee_id = models.CharField(max_length=50, unique=True, verbose_name='工号')
    department = models.CharField(max_length=100, blank=True, null=True, verbose_name='部门')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='联系电话')
    is_active = models.BooleanField(default=True, verbose_name='是否在职')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'responsible_person'
        verbose_name = '责任人'
        verbose_name_plural = verbose_name
        ordering = ['employee_id']

    def __str__(self):
        return f'{self.employee_id} - {self.name}'


class Book(models.Model):
    book_no = models.CharField(max_length=100, unique=True, verbose_name='书册编号')
    title = models.CharField(max_length=200, verbose_name='书名')
    paper_type = models.ForeignKey(PaperType, on_delete=models.PROTECT, verbose_name='纸张类型')
    binding_type = models.ForeignKey(BindingType, on_delete=models.PROTECT, verbose_name='装订形式')
    page_count = models.IntegerField(default=0, verbose_name='页数')
    description = models.TextField(blank=True, null=True, verbose_name='书册描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'book'
        verbose_name = '书册'
        verbose_name_plural = verbose_name
        ordering = ['book_no']

    def __str__(self):
        return f'{self.book_no} - {self.title}'

    @property
    def current_work_order(self):
        return self.workorder_set.filter(status__in=WorkOrder.ACTIVE_STATUSES).first()


class WorkOrder(models.Model):
    STATUS_PENDING_RECEIVE = 'pending_receive'
    STATUS_PROCESSING = 'processing'
    STATUS_PENDING_PRESS = 'pending_press'
    STATUS_PENDING_REVIEW = 'pending_review'
    STATUS_REWORKING = 'reworking'
    STATUS_STORABLE = 'storable'
    STATUS_PAUSED = 'paused'

    STATUS_CHOICES = [
        (STATUS_PENDING_RECEIVE, '待接收'),
        (STATUS_PROCESSING, '处理中'),
        (STATUS_PENDING_PRESS, '待压平'),
        (STATUS_PENDING_REVIEW, '待复核'),
        (STATUS_REWORKING, '返工中'),
        (STATUS_STORABLE, '可入库'),
        (STATUS_PAUSED, '暂停处理'),
    ]

    ACTIVE_STATUSES = [
        STATUS_PENDING_RECEIVE,
        STATUS_PROCESSING,
        STATUS_PENDING_PRESS,
        STATUS_PENDING_REVIEW,
        STATUS_REWORKING,
        STATUS_PAUSED,
    ]

    FINISHED_STATUSES = [STATUS_STORABLE]

    order_no = models.CharField(max_length=100, unique=True, verbose_name='工单编号')
    book = models.ForeignKey(Book, on_delete=models.PROTECT, verbose_name='书册')
    work_station = models.ForeignKey(WorkStation, on_delete=models.PROTECT, verbose_name='处理台位')
    responsible_person = models.ForeignKey(
        ResponsiblePerson, on_delete=models.PROTECT, verbose_name='责任人'
    )
    restorer = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='restore_orders',
        limit_choices_to={'role': User.ROLE_RESTORER}, verbose_name='修护师'
    )
    reviewer = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='review_orders',
        limit_choices_to={'role': User.ROLE_REVIEWER},
        blank=True, null=True, verbose_name='复核员'
    )
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES,
        default=STATUS_PENDING_RECEIVE, verbose_name='状态'
    )
    review_interval_hours = models.IntegerField(default=24, verbose_name='复核间隔(小时)')
    damage_description = models.TextField(blank=True, null=True, verbose_name='破损说明')
    process_remark = models.TextField(blank=True, null=True, verbose_name='处理备注')
    receive_time = models.DateTimeField(blank=True, null=True, verbose_name='接收时间')
    start_time = models.DateTimeField(blank=True, null=True, verbose_name='开始处理时间')
    press_start_time = models.DateTimeField(blank=True, null=True, verbose_name='压平开始时间')
    press_complete_time = models.DateTimeField(blank=True, null=True, verbose_name='压平完成时间')
    review_submit_time = models.DateTimeField(blank=True, null=True, verbose_name='提交复核时间')
    complete_time = models.DateTimeField(blank=True, null=True, verbose_name='完成时间')
    rework_count = models.IntegerField(default=0, verbose_name='返工次数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'work_order'
        verbose_name = '工单'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order_no} - {self.book.book_no}'

    def clean(self):
        if self.pk is None:
            active_orders = WorkOrder.objects.filter(
                book=self.book, status__in=self.ACTIVE_STATUSES
            ).exclude(pk=self.pk)
            if active_orders.exists():
                raise ValidationError('该书册存在未结束的工单，无法创建新工单')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @property
    def process_duration_hours(self):
        if self.start_time and self.complete_time:
            delta = self.complete_time - self.start_time
            return round(delta.total_seconds() / 3600, 2)
        if self.start_time:
            delta = timezone.now() - self.start_time
            return round(delta.total_seconds() / 3600, 2)
        return 0


class RepairRecord(models.Model):
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE, related_name='repair_records', verbose_name='工单'
    )
    restorer = models.ForeignKey(
        User, on_delete=models.PROTECT, limit_choices_to={'role': User.ROLE_RESTORER},
        verbose_name='修护师'
    )
    has_page_separation = models.BooleanField(default=False, verbose_name='是否拆页')
    has_paper_repair = models.BooleanField(default=False, verbose_name='是否补纸')
    has_pressing = models.BooleanField(default=False, verbose_name='是否压平')
    has_binding = models.BooleanField(default=False, verbose_name='是否装订')
    damage_description = models.TextField(blank=True, null=True, verbose_name='破损说明')
    process_remark = models.TextField(blank=True, null=True, verbose_name='处理备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='记录时间')

    class Meta:
        db_table = 'repair_record'
        verbose_name = '修护记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.work_order.order_no} - 修护记录'


class ReviewRecord(models.Model):
    RESULT_PASS = 'pass'
    RESULT_REWORK = 'rework'
    RESULT_PENDING = 'pending'

    RESULT_CHOICES = [
        (RESULT_PASS, '通过'),
        (RESULT_REWORK, '返工'),
        (RESULT_PENDING, '待补充'),
    ]

    FLATNESS_GOOD = 'good'
    FLATNESS_NORMAL = 'normal'
    FLATNESS_POOR = 'poor'

    FLATNESS_CHOICES = [
        (FLATNESS_GOOD, '良好'),
        (FLATNESS_NORMAL, '一般'),
        (FLATNESS_POOR, '较差'),
    ]

    PAGE_ORDER_CORRECT = 'correct'
    PAGE_ORDER_WRONG = 'wrong'
    PAGE_ORDER_MISSING = 'missing'

    PAGE_ORDER_CHOICES = [
        (PAGE_ORDER_CORRECT, '正确'),
        (PAGE_ORDER_WRONG, '顺序错误'),
        (PAGE_ORDER_MISSING, '缺页'),
    ]

    COVER_GOOD = 'good'
    COVER_NORMAL = 'normal'
    COVER_DAMAGED = 'damaged'

    COVER_CHOICES = [
        (COVER_GOOD, '完好'),
        (COVER_NORMAL, '一般'),
        (COVER_DAMAGED, '破损'),
    ]

    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE, related_name='review_records', verbose_name='工单'
    )
    reviewer = models.ForeignKey(
        User, on_delete=models.PROTECT, limit_choices_to={'role': User.ROLE_REVIEWER},
        verbose_name='复核员'
    )
    flatness = models.CharField(max_length=20, choices=FLATNESS_CHOICES, verbose_name='平整度')
    page_order = models.CharField(max_length=20, choices=PAGE_ORDER_CHOICES, verbose_name='页序核对')
    cover_status = models.CharField(max_length=20, choices=COVER_CHOICES, verbose_name='封面状态')
    conclusion = models.CharField(max_length=20, choices=RESULT_CHOICES, verbose_name='最终结论')
    rework_reason = models.TextField(blank=True, null=True, verbose_name='返工原因')
    review_remark = models.TextField(blank=True, null=True, verbose_name='复核备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='复核时间')

    class Meta:
        db_table = 'review_record'
        verbose_name = '复核记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.work_order.order_no} - {self.get_conclusion_display()}'
