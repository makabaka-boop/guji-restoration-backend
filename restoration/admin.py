from django.contrib import admin
from .models import User, BookVolume, WorkOrder, ReviewRecord, Alert


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'role', 'is_active')
    list_filter = ('role', 'is_active')


@admin.register(BookVolume)
class BookVolumeAdmin(admin.ModelAdmin):
    list_display = ('code', 'paper_type', 'binding_form', 'station', 'responsible', 'review_interval_days')
    list_filter = ('paper_type', 'binding_form')
    search_fields = ('code',)


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'book', 'status', 'operator', 'rework_count', 'created_at')
    list_filter = ('status',)
    search_fields = ('book__code',)


@admin.register(ReviewRecord)
class ReviewRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'work_order', 'reviewer', 'flatness', 'page_order_check', 'cover_status', 'conclusion', 'created_at')
    list_filter = ('conclusion', 'flatness', 'page_order_check', 'cover_status')


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'alert_type', 'work_order', 'is_resolved', 'created_at')
    list_filter = ('alert_type', 'is_resolved')
