from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, PaperType, BindingType, Workstation, Book,
    WorkOrder, RestorationRecord, ReviewRecord, StatusLog
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'role', 'email', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('角色信息', {'fields': ('role', 'phone')}),
    )


@admin.register(PaperType)
class PaperTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)


@admin.register(BindingType)
class BindingTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)


@admin.register(Workstation)
class WorkstationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'location', 'created_at')
    search_fields = ('name',)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('id', 'book_no', 'title', 'paper_type', 'binding_type', 'total_pages', 'created_at')
    list_filter = ('paper_type', 'binding_type')
    search_fields = ('book_no', 'title')


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'book', 'workstation', 'restorer', 'status',
                    'rework_count', 'created_at')
    list_filter = ('status', 'workstation', 'restorer')
    search_fields = ('book__book_no', 'book__title')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RestorationRecord)
class RestorationRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'work_order', 'restorer', 'created_at')
    list_filter = ('restorer',)
    search_fields = ('work_order__book__book_no',)


@admin.register(ReviewRecord)
class ReviewRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'work_order', 'reviewer', 'conclusion', 'created_at')
    list_filter = ('conclusion', 'reviewer')
    search_fields = ('work_order__book__book_no',)


@admin.register(StatusLog)
class StatusLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'work_order', 'from_status', 'to_status', 'operator', 'created_at')
    list_filter = ('from_status', 'to_status', 'operator')
    search_fields = ('work_order__book__book_no',)
