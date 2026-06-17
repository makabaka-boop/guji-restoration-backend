from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    ROLE_ADMIN = 'admin'
    ROLE_RESTORER = 'restorer'
    ROLE_REVIEWER = 'reviewer'
    ROLE_CHOICES = [
        (ROLE_ADMIN, '管理员'),
        (ROLE_RESTORER, '修护师'),
        (ROLE_REVIEWER, '复核员'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_RESTORER)
    phone = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = 'sys_user'


class PaperType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='纸张类型')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'paper_type'
        ordering = ['-id']

    def __str__(self):
        return self.name


class BindingType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='装订形式')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'binding_type'
        ordering = ['-id']

    def __str__(self):
        return self.name


class Workstation(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='台位名称')
    location = models.CharField(max_length=200, blank=True, null=True, verbose_name='位置')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workstation'
        ordering = ['-id']

    def __str__(self):
        return self.name


class Book(models.Model):
    book_no = models.CharField(max_length=100, unique=True, verbose_name='书册编号')
    title = models.CharField(max_length=200, verbose_name='书名')
    paper_type = models.ForeignKey(PaperType, on_delete=models.PROTECT, verbose_name='纸张类型')
    binding_type = models.ForeignKey(BindingType, on_delete=models.PROTECT, verbose_name='装订形式')
    total_pages = models.IntegerField(default=0, verbose_name='总页数')
    description = models.TextField(blank=True, null=True, verbose_name='书册描述')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'book'
        ordering = ['-id']

    def __str__(self):
        return f'{self.book_no} - {self.title}'


class WorkOrder(models.Model):
    STATUS_PENDING_RECEIPT = 'pending_receipt'
    STATUS_PROCESSING = 'processing'
    STATUS_PENDING_PRESSING = 'pending_pressing'
    STATUS_PENDING_REVIEW = 'pending_review'
    STATUS_REWORKING = 'reworking'
    STATUS_READY_STORAGE = 'ready_for_storage'
    STATUS_SUSPENDED = 'suspended'

    STATUS_CHOICES = [
        (STATUS_PENDING_RECEIPT, '待接收'),
        (STATUS_PROCESSING, '处理中'),
        (STATUS_PENDING_PRESSING, '待压平'),
        (STATUS_PENDING_REVIEW, '待复核'),
        (STATUS_REWORKING, '返工中'),
        (STATUS_READY_STORAGE, '可入库'),
        (STATUS_SUSPENDED, '暂停处理'),
    ]

    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name='work_orders', verbose_name='书册')
    workstation = models.ForeignKey(Workstation, on_delete=models.PROTECT, verbose_name='处理台位')
    restorer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='restoration_orders',
                                 limit_choices_to={'role': User.ROLE_RESTORER}, verbose_name='责任人')
    reviewer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='review_orders',
                                 limit_choices_to={'role': User.ROLE_REVIEWER}, verbose_name='复核员',
                                 blank=True, null=True)
    review_interval_days = models.IntegerField(default=3, verbose_name='复核间隔（天）')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES,
                              default=STATUS_PENDING_RECEIPT, verbose_name='状态')

    received_at = models.DateTimeField(blank=True, null=True, verbose_name='接收时间')
    started_at = models.DateTimeField(blank=True, null=True, verbose_name='开始处理时间')
    pressing_completed_at = models.DateTimeField(blank=True, null=True, verbose_name='压平完成时间')
    review_due_at = models.DateTimeField(blank=True, null=True, verbose_name='复核到期时间')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='完成时间')
    suspended_at = models.DateTimeField(blank=True, null=True, verbose_name='暂停时间')

    rework_count = models.IntegerField(default=0, verbose_name='返工次数')
    rework_reason = models.TextField(blank=True, null=True, verbose_name='最近返工原因')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'work_order'
        ordering = ['-created_at']

    def __str__(self):
        return f'工单#{self.id} - {self.book.book_no}'

    @classmethod
    def has_active_order(cls, book_id):
        active_statuses = [
            cls.STATUS_PENDING_RECEIPT,
            cls.STATUS_PROCESSING,
            cls.STATUS_PENDING_PRESSING,
            cls.STATUS_PENDING_REVIEW,
            cls.STATUS_REWORKING,
            cls.STATUS_SUSPENDED,
        ]
        return cls.objects.filter(book_id=book_id, status__in=active_statuses).exists()

    def processing_days(self):
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).days
        if self.started_at:
            return (timezone.now() - self.started_at).days
        return 0


class RestorationRecord(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE,
                                   related_name='restoration_records', verbose_name='工单')
    restorer = models.ForeignKey(User, on_delete=models.PROTECT,
                                 limit_choices_to={'role': User.ROLE_RESTORER}, verbose_name='修护师')
    disassembly_pages = models.TextField(blank=True, null=True, verbose_name='拆页情况')
    paper_repair = models.TextField(blank=True, null=True, verbose_name='补纸情况')
    pressing = models.TextField(blank=True, null=True, verbose_name='压平情况')
    binding = models.TextField(blank=True, null=True, verbose_name='装订情况')
    damage_description = models.TextField(blank=True, null=True, verbose_name='破损说明')
    processing_notes = models.TextField(blank=True, null=True, verbose_name='处理备注')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'restoration_record'
        ordering = ['-created_at']

    def __str__(self):
        return f'修护记录-{self.id}'


class ReviewRecord(models.Model):
    CONCLUSION_PASS = 'pass'
    CONCLUSION_REWORK = 'rework'
    CONCLUSION_CHOICES = [
        (CONCLUSION_PASS, '通过'),
        (CONCLUSION_REWORK, '返工'),
    ]

    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE,
                                   related_name='review_records', verbose_name='工单')
    reviewer = models.ForeignKey(User, on_delete=models.PROTECT,
                                 limit_choices_to={'role': User.ROLE_REVIEWER}, verbose_name='复核员')
    flatness = models.TextField(verbose_name='平整度')
    page_order_check = models.TextField(verbose_name='页序核对')
    cover_status = models.TextField(verbose_name='封面状态')
    conclusion = models.CharField(max_length=20, choices=CONCLUSION_CHOICES, verbose_name='最终结论')
    rework_reason = models.TextField(blank=True, null=True, verbose_name='返工原因')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'review_record'
        ordering = ['-created_at']

    def __str__(self):
        return f'复核记录-{self.id}'


class StatusLog(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE,
                                   related_name='status_logs', verbose_name='工单')
    from_status = models.CharField(max_length=30, blank=True, null=True, verbose_name='原状态')
    to_status = models.CharField(max_length=30, verbose_name='目标状态')
    operator = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='操作人')
    remark = models.TextField(blank=True, null=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'status_log'
        ordering = ['-created_at']

    def __str__(self):
        return f'状态流转-{self.id}'
