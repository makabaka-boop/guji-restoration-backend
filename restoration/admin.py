from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, PaperType, BindingType, WorkStation, ResponsiblePerson,
    Book, WorkOrder, RepairRecord, ReviewRecord
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'role', 'email', 'is_staff', 'is_active']
    list_filter = ['role', 'is_staff', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('角色信息', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('角色信息', {'fields': ('role', 'phone')}),
    )


@admin.register(PaperType)
class PaperTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'created_at', 'updated_at']
    search_fields = ['name']


@admin.register(BindingType)
class BindingTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'created_at', 'updated_at']
    search_fields = ['name']


@admin.register(WorkStation)
class WorkStationAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['code', 'name']


@admin.register(ResponsiblePerson)
class ResponsiblePersonAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'name', 'department', 'phone', 'is_active']
    list_filter = ['is_active', 'department']
    search_fields = ['employee_id', 'name']


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['book_no', 'title', 'paper_type', 'binding_type', 'page_count']
    list_filter = ['paper_type', 'binding_type']
    search_fields = ['book_no', 'title']


class RepairRecordInline(admin.TabularInline):
    model = RepairRecord
    extra = 0
    readonly_fields = ['created_at']


class ReviewRecordInline(admin.TabularInline):
    model = ReviewRecord
    extra = 0
    readonly_fields = ['created_at']


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_no', 'book', 'work_station', 'responsible_person',
        'restorer', 'status', 'rework_count', 'created_at'
    ]
    list_filter = ['status', 'work_station']
    search_fields = ['order_no', 'book__book_no', 'book__title']
    readonly_fields = ['order_no', 'created_at', 'updated_at']
    inlines = [RepairRecordInline, ReviewRecordInline]


@admin.register(RepairRecord)
class RepairRecordAdmin(admin.ModelAdmin):
    list_display = [
        'work_order', 'restorer', 'has_page_separation', 'has_paper_repair',
        'has_pressing', 'has_binding', 'created_at'
    ]
    list_filter = ['has_page_separation', 'has_paper_repair', 'has_pressing', 'has_binding']
    search_fields = ['work_order__order_no']
    readonly_fields = ['created_at']


@admin.register(ReviewRecord)
class ReviewRecordAdmin(admin.ModelAdmin):
    list_display = [
        'work_order', 'reviewer', 'flatness', 'page_order',
        'cover_status', 'conclusion', 'created_at'
    ]
    list_filter = ['flatness', 'page_order', 'cover_status', 'conclusion']
    search_fields = ['work_order__order_no']
    readonly_fields = ['created_at']
