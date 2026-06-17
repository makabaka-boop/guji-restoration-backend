from rest_framework import serializers
from django.utils import timezone
from .models import User, BookVolume, WorkOrder, ReviewRecord, Alert


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'role', 'is_active')
        read_only_fields = ('id',)


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'role', 'is_active')
        read_only_fields = ('id',)

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class BookVolumeSerializer(serializers.ModelSerializer):
    responsible_name = serializers.CharField(source='responsible.username', read_only=True, default='')

    class Meta:
        model = BookVolume
        fields = (
            'id', 'code', 'paper_type', 'binding_form', 'station',
            'responsible', 'responsible_name', 'review_interval_days',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class WorkOrderListSerializer(serializers.ModelSerializer):
    book_code = serializers.CharField(source='book.code', read_only=True)
    book_paper_type = serializers.CharField(source='book.paper_type', read_only=True)
    operator_name = serializers.CharField(source='operator.username', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = WorkOrder
        fields = (
            'id', 'book', 'book_code', 'book_paper_type', 'status', 'status_display',
            'operator', 'operator_name', 'rework_count', 'rework_reason',
            'pressing_completed_at', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class WorkOrderDetailSerializer(WorkOrderListSerializer):
    class Meta(WorkOrderListSerializer.Meta):
        fields = WorkOrderListSerializer.Meta.fields + (
            'page_removal', 'paper_repair', 'pressing', 'binding',
            'damage_description', 'processing_notes',
        )


class WorkOrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = ('id', 'book')
        read_only_fields = ('id',)

    def validate_book(self, value):
        active_orders = WorkOrder.objects.filter(
            book=value, status__in=WorkOrder.ACTIVE_STATUSES
        )
        if active_orders.exists():
            raise serializers.ValidationError(
                f'书册 {value.code} 已存在未结束工单，不能重复创建'
            )
        return value


class RestorationSubmitSerializer(serializers.Serializer):
    page_removal = serializers.CharField(required=False, allow_blank=True, default='')
    paper_repair = serializers.CharField(required=False, allow_blank=True, default='')
    pressing = serializers.CharField(required=False, allow_blank=True, default='')
    binding = serializers.CharField(required=False, allow_blank=True, default='')
    damage_description = serializers.CharField(required=False, allow_blank=True, default='')
    processing_notes = serializers.CharField(required=False, allow_blank=True, default='')


class ReviewRecordSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True, default='')

    class Meta:
        model = ReviewRecord
        fields = (
            'id', 'work_order', 'reviewer', 'reviewer_name',
            'flatness', 'page_order_check', 'cover_status',
            'conclusion', 'remark', 'created_at',
        )
        read_only_fields = ('id', 'reviewer', 'created_at')


class ReviewSubmitSerializer(serializers.Serializer):
    flatness = serializers.ChoiceField(choices=['qualified', 'unqualified'])
    page_order_check = serializers.ChoiceField(choices=['correct', 'incorrect'])
    cover_status = serializers.ChoiceField(choices=['intact', 'damaged'])
    conclusion = serializers.ChoiceField(choices=['pass', 'rework'])
    remark = serializers.CharField(required=False, allow_blank=True, default='')


class AlertSerializer(serializers.ModelSerializer):
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    book_code = serializers.CharField(source='work_order.book.code', read_only=True, default='')

    class Meta:
        model = Alert
        fields = (
            'id', 'alert_type', 'alert_type_display', 'work_order', 'book_code',
            'message', 'is_resolved', 'created_at',
        )
        read_only_fields = ('id', 'created_at')


class StatusTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=WorkOrder.STATUS_CHOICES)


class ReworkSubmitSerializer(serializers.Serializer):
    rework_reason = serializers.CharField(required=True, allow_blank=False)
