from rest_framework import serializers
from .models import (
    User, PaperType, BindingType, Station, Book,
    WorkOrder, RestorationRecord, ReviewRecord, StatusLog,
    ROLE_CHOICES, STATUS_CHOICES,
)


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'role', 'role_display', 'email', 'phone', 'first_name', 'last_name']
        read_only_fields = ['id']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'role', 'email', 'phone', 'first_name', 'last_name']
        read_only_fields = ['id']

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class PaperTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperType
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class BindingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BindingType
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ['id', 'name', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class BookSerializer(serializers.ModelSerializer):
    paper_type_name = serializers.CharField(source='paper_type.name', read_only=True)
    binding_type_name = serializers.CharField(source='binding_type.name', read_only=True)
    default_station_name = serializers.CharField(source='default_station.name', read_only=True)
    default_restorer_name = serializers.CharField(source='default_restorer.username', read_only=True)
    has_active_order = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'book_number', 'paper_type', 'paper_type_name',
            'binding_type', 'binding_type_name', 'default_station',
            'default_station_name', 'default_restorer', 'default_restorer_name',
            'review_interval_days', 'description', 'has_active_order',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_has_active_order(self, obj):
        return obj.active_work_order is not None

    def validate_default_restorer(self, value):
        if value and value.role != 'restorer':
            raise serializers.ValidationError('默认责任人必须是修护师角色')
        return value


class BookListSerializer(serializers.ModelSerializer):
    paper_type_name = serializers.CharField(source='paper_type.name', read_only=True)
    binding_type_name = serializers.CharField(source='binding_type.name', read_only=True)
    default_station_name = serializers.CharField(source='default_station.name', read_only=True)
    default_restorer_name = serializers.CharField(source='default_restorer.username', read_only=True)

    class Meta:
        model = Book
        fields = [
            'id', 'book_number', 'paper_type_name', 'binding_type_name',
            'default_station_name', 'default_restorer_name',
            'review_interval_days', 'created_at',
        ]


class StatusLogSerializer(serializers.ModelSerializer):
    from_status_display = serializers.CharField(source='get_from_status_display', read_only=True)
    to_status_display = serializers.CharField(source='get_to_status_display', read_only=True)
    operator_name = serializers.CharField(source='operator.username', read_only=True)

    class Meta:
        model = StatusLog
        fields = [
            'id', 'from_status', 'from_status_display', 'to_status',
            'to_status_display', 'operator_name', 'remark', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class RestorationRecordSerializer(serializers.ModelSerializer):
    restorer_name = serializers.CharField(source='restorer.username', read_only=True)
    press_level_display = serializers.CharField(source='get_press_level_display', read_only=True)

    class Meta:
        model = RestorationRecord
        fields = [
            'id', 'work_order', 'restorer', 'restorer_name',
            'disassembly_done', 'disassembly_note',
            'paper_repair_done', 'paper_repair_note',
            'press_done', 'press_level', 'press_level_display',
            'press_duration_hours', 'press_note',
            'binding_done', 'binding_note',
            'damage_description', 'handling_note', 'created_at',
        ]
        read_only_fields = ['id', 'work_order', 'restorer', 'created_at']


class ReviewRecordSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True)
    flatness_display = serializers.CharField(source='get_flatness_display', read_only=True)
    cover_status_display = serializers.CharField(source='get_cover_status_display', read_only=True)
    conclusion_display = serializers.CharField(source='get_conclusion_display', read_only=True)

    class Meta:
        model = ReviewRecord
        fields = [
            'id', 'work_order', 'reviewer', 'reviewer_name',
            'flatness', 'flatness_display', 'flatness_note',
            'page_order_correct', 'page_order_note',
            'cover_status', 'cover_status_display', 'cover_note',
            'conclusion', 'conclusion_display', 'rework_reason',
            'review_note', 'created_at',
        ]
        read_only_fields = ['id', 'work_order', 'reviewer', 'created_at']


class WorkOrderSerializer(serializers.ModelSerializer):
    book_number = serializers.CharField(source='book.book_number', read_only=True)
    station_name = serializers.CharField(source='station.name', read_only=True)
    restorer_name = serializers.CharField(source='restorer.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    processing_cycle_hours = serializers.FloatField(read_only=True)
    is_review_overdue = serializers.BooleanField(read_only=True)
    paper_type_name = serializers.CharField(source='book.paper_type.name', read_only=True)
    binding_type_name = serializers.CharField(source='book.binding_type.name', read_only=True)
    restoration_records = RestorationRecordSerializer(many=True, read_only=True)
    review_records = ReviewRecordSerializer(many=True, read_only=True)
    status_logs = StatusLogSerializer(many=True, read_only=True)

    class Meta:
        model = WorkOrder
        fields = [
            'id', 'order_no', 'book', 'book_number', 'status', 'status_display',
            'station', 'station_name', 'restorer', 'restorer_name',
            'paper_type_name', 'binding_type_name',
            'review_interval_days', 'received_at', 'processing_started_at',
            'press_started_at', 'press_completed_at', 'review_due_at',
            'review_completed_at', 'completed_at', 'rework_count',
            'pause_reason', 'processing_cycle_hours', 'is_review_overdue',
            'restoration_records', 'review_records', 'status_logs',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'order_no', 'status', 'received_at', 'processing_started_at',
            'press_started_at', 'press_completed_at', 'review_due_at',
            'review_completed_at', 'completed_at', 'rework_count',
            'processing_cycle_hours', 'is_review_overdue',
            'restoration_records', 'review_records', 'status_logs',
            'created_at', 'updated_at',
        ]


class WorkOrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = ['book', 'station', 'restorer', 'review_interval_days']

    def validate_book(self, value):
        active = value.workorder_set.exclude(status='storable').first()
        if active:
            raise serializers.ValidationError(f'该书册存在未结束工单: {active.order_no}')
        return value

    def validate_restorer(self, value):
        if value.role != 'restorer':
            raise serializers.ValidationError('责任人必须是修护师角色')
        return value


class WorkOrderListSerializer(serializers.ModelSerializer):
    book_number = serializers.CharField(source='book.book_number', read_only=True)
    station_name = serializers.CharField(source='station.name', read_only=True)
    restorer_name = serializers.CharField(source='restorer.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    paper_type_name = serializers.CharField(source='book.paper_type.name', read_only=True)
    processing_cycle_hours = serializers.FloatField(read_only=True)
    is_review_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = WorkOrder
        fields = [
            'id', 'order_no', 'book_number', 'status', 'status_display',
            'station_name', 'restorer_name', 'paper_type_name',
            'rework_count', 'processing_cycle_hours', 'is_review_overdue',
            'created_at', 'updated_at',
        ]


class RestorationSubmitSerializer(serializers.Serializer):
    disassembly_done = serializers.BooleanField(default=False)
    disassembly_note = serializers.CharField(allow_blank=True, required=False)
    paper_repair_done = serializers.BooleanField(default=False)
    paper_repair_note = serializers.CharField(allow_blank=True, required=False)
    press_done = serializers.BooleanField(default=False)
    press_level = serializers.CharField(allow_blank=True, required=False)
    press_duration_hours = serializers.FloatField(required=False, allow_null=True)
    press_note = serializers.CharField(allow_blank=True, required=False)
    binding_done = serializers.BooleanField(default=False)
    binding_note = serializers.CharField(allow_blank=True, required=False)
    damage_description = serializers.CharField(allow_blank=True, required=False)
    handling_note = serializers.CharField(allow_blank=True, required=False)


class ReviewSubmitSerializer(serializers.Serializer):
    flatness = serializers.CharField()
    flatness_note = serializers.CharField(allow_blank=True, required=False)
    page_order_correct = serializers.BooleanField(default=True)
    page_order_note = serializers.CharField(allow_blank=True, required=False)
    cover_status = serializers.CharField()
    cover_note = serializers.CharField(allow_blank=True, required=False)
    conclusion = serializers.CharField()
    rework_reason = serializers.CharField(allow_blank=True, required=False)
    review_note = serializers.CharField(allow_blank=True, required=False)


class PauseSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=False)


class StatisticsSerializer(serializers.Serializer):
    rework_reason_distribution = serializers.ListField(child=serializers.DictField())
    pending_review_books = serializers.IntegerField()
    processing_cycle_ranges = serializers.ListField(child=serializers.DictField())


class AnomalySerializer(serializers.Serializer):
    review_overdue = serializers.ListField(child=serializers.DictField())
    high_rework_by_paper = serializers.ListField(child=serializers.DictField())
    no_review_after_press = serializers.ListField(child=serializers.DictField())
    abnormal_cycle = serializers.ListField(child=serializers.DictField())
