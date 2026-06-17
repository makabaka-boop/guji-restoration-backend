from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    User, PaperType, BindingType, Station, Book, WorkOrder,
    RestorationRecord, ReviewRecord, StatusLog,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'role', 'email', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('角色信息', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('角色信息', {'fields': ('role', 'phone')}),
    )


@admin.register(PaperType)
class PaperTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(BindingType)
class BindingTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']


class WorkOrderInline(admin.TabularInline):
    model = WorkOrder
    extra = 0
    fields = ['order_no', 'status', 'restorer', 'station', 'created_at']
    readonly_fields = ['order_no', 'status', 'restorer', 'station', 'created_at']


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['book_number', 'paper_type', 'binding_type', 'default_restorer', 'review_interval_days', 'created_at']
    list_filter = ['paper_type', 'binding_type']
    search_fields = ['book_number']
    inlines = [WorkOrderInline]


class RestorationRecordInline(admin.TabularInline):
    model = RestorationRecord
    extra = 0
    readonly_fields = ['created_at']


class ReviewRecordInline(admin.TabularInline):
    model = ReviewRecord
    extra = 0
    readonly_fields = ['created_at']


class StatusLogInline(admin.TabularInline):
    model = StatusLog
    extra = 0
    readonly_fields = ['from_status', 'to_status', 'operator', 'created_at']


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ['order_no', 'book', 'status', 'restorer', 'station', 'rework_count', 'created_at']
    list_filter = ['status', 'station']
    search_fields = ['order_no', 'book__book_number', 'restorer__username']
    readonly_fields = ['order_no', 'created_at', 'updated_at']
    inlines = [RestorationRecordInline, ReviewRecordInline, StatusLogInline]


@admin.register(RestorationRecord)
class RestorationRecordAdmin(admin.ModelAdmin):
    list_display = ['work_order', 'restorer', 'disassembly_done', 'paper_repair_done', 'press_done', 'binding_done', 'created_at']
    list_filter = ['disassembly_done', 'paper_repair_done', 'press_done', 'binding_done']
    search_fields = ['work_order__order_no', 'restorer__username']


@admin.register(ReviewRecord)
class ReviewRecordAdmin(admin.ModelAdmin):
    list_display = ['work_order', 'reviewer', 'flatness', 'conclusion', 'created_at']
    list_filter = ['conclusion', 'flatness', 'cover_status']
    search_fields = ['work_order__order_no', 'reviewer__username']


@admin.register(StatusLog)
class StatusLogAdmin(admin.ModelAdmin):
    list_display = ['work_order', 'from_status', 'to_status', 'operator', 'created_at']
    list_filter = ['from_status', 'to_status']
    search_fields = ['work_order__order_no', 'operator__username']
