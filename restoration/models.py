from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', '管理员'),
        ('restorer', '修护师'),
        ('reviewer', '复核员'),
    )
    role = models.CharField('角色', max_length=20, choices=ROLE_CHOICES, default='restorer')

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return f'{self.username}({self.get_role_display()})'


class BookVolume(models.Model):
    code = models.CharField('书册编号', max_length=64, unique=True)
    paper_type = models.CharField('纸张类型', max_length=64)
    binding_form = models.CharField('装订形式', max_length=64)
    station = models.CharField('处理台位', max_length=64, blank=True, default='')
    responsible = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='responsible_books', verbose_name='责任人',
    )
    review_interval_days = models.PositiveIntegerField('复核间隔(天)', default=7)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '书册'
        verbose_name_plural = '书册'
        ordering = ['-created_at']

    def __str__(self):
        return self.code


class WorkOrder(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_PENDING_PRESSING = 'pending_pressing'
    STATUS_PENDING_REVIEW = 'pending_review'
    STATUS_REWORK = 'rework'
    STATUS_CAN_STORE = 'can_store'
    STATUS_SUSPENDED = 'suspended'

    STATUS_CHOICES = (
        (STATUS_PENDING, '待接收'),
        (STATUS_PROCESSING, '处理中'),
        (STATUS_PENDING_PRESSING, '待压平'),
        (STATUS_PENDING_REVIEW, '待复核'),
        (STATUS_REWORK, '返工中'),
        (STATUS_CAN_STORE, '可入库'),
        (STATUS_SUSPENDED, '暂停处理'),
    )

    ACTIVE_STATUSES = [
        STATUS_PENDING, STATUS_PROCESSING, STATUS_PENDING_PRESSING,
        STATUS_PENDING_REVIEW, STATUS_REWORK, STATUS_SUSPENDED,
    ]

    book = models.ForeignKey(
        BookVolume, on_delete=models.CASCADE,
        related_name='work_orders', verbose_name='书册',
    )
    status = models.CharField('状态', max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    operator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='operated_orders', verbose_name='修护师',
    )
    page_removal = models.TextField('拆页说明', blank=True, default='')
    paper_repair = models.TextField('补纸说明', blank=True, default='')
    pressing = models.TextField('压平说明', blank=True, default='')
    binding = models.TextField('装订说明', blank=True, default='')
    damage_description = models.TextField('破损说明', blank=True, default='')
    processing_notes = models.TextField('处理备注', blank=True, default='')
    rework_reason = models.TextField('返工原因', blank=True, default='')
    rework_count = models.PositiveIntegerField('返工次数', default=0)
    pressing_completed_at = models.DateTimeField('压平完成时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '工单'
        verbose_name_plural = '工单'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.book.code}-{self.get_status_display()}-{self.id}'


class ReviewRecord(models.Model):
    FLATNESS_CHOICES = (
        ('qualified', '合格'),
        ('unqualified', '不合格'),
    )
    PAGE_ORDER_CHOICES = (
        ('correct', '正确'),
        ('incorrect', '不正确'),
    )
    COVER_CHOICES = (
        ('intact', '完好'),
        ('damaged', '损坏'),
    )
    CONCLUSION_CHOICES = (
        ('pass', '通过'),
        ('rework', '返工'),
    )

    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE,
        related_name='reviews', verbose_name='工单',
    )
    reviewer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='reviews', verbose_name='复核员',
    )
    flatness = models.CharField('平整度', max_length=20, choices=FLATNESS_CHOICES)
    page_order_check = models.CharField('页序核对', max_length=20, choices=PAGE_ORDER_CHOICES)
    cover_status = models.CharField('封面状态', max_length=20, choices=COVER_CHOICES)
    conclusion = models.CharField('最终结论', max_length=20, choices=CONCLUSION_CHOICES)
    remark = models.TextField('备注', blank=True, default='')
    created_at = models.DateTimeField('复核时间', auto_now_add=True)

    class Meta:
        verbose_name = '复核记录'
        verbose_name_plural = '复核记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'复核-{self.work_order.id}-{self.get_conclusion_display()}'


class Alert(models.Model):
    ALERT_TYPE_CHOICES = (
        ('review_overdue', '复核超期'),
        ('high_rework', '同纸张返工偏多'),
        ('no_review_after_pressing', '压平后无复核'),
        ('abnormal_cycle', '处理周期异常'),
    )

    alert_type = models.CharField('预警类型', max_length=40, choices=ALERT_TYPE_CHOICES)
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE,
        related_name='alerts', null=True, blank=True, verbose_name='关联工单',
    )
    message = models.TextField('预警信息')
    is_resolved = models.BooleanField('是否已处理', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '预警'
        verbose_name_plural = '预警'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.get_alert_type_display()}] {self.message[:50]}'
