from rest_framework import serializers
from .models import (
    User, PaperType, BindingType, Workstation, Book,
    WorkOrder, RestorationRecord, ReviewRecord, StatusLog
)


class UserSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email',
                  'role', 'role_label', 'phone', 'is_active']
        read_only_fields = ['id']


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


class WorkstationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workstation
        fields = ['id', 'name', 'location', 'created_at']
        read_only_fields = ['id', 'created_at']


class BookSerializer(serializers.ModelSerializer):
    paper_type_name = serializers.CharField(source='paper_type.name', read_only=True)
    binding_type_name = serializers.CharField(source='binding_type.name', read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'book_no', 'title', 'paper_type', 'paper_type_name',
                  'binding_type', 'binding_type_name', 'total_pages',
                  'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class BookListSerializer(serializers.ModelSerializer):
    paper_type_name = serializers.CharField(source='paper_type.name', read_only=True)
    binding_type_name = serializers.CharField(source='binding_type.name', read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'book_no', 'title', 'paper_type_name', 'binding_type_name',
                  'total_pages', 'created_at']


class RestorationRecordSerializer(serializers.ModelSerializer):
    restorer_name = serializers.CharField(source='restorer.get_full_name', read_only=True)

    class Meta:
        model = RestorationRecord
        fields = ['id', 'work_order', 'restorer', 'restorer_name',
                  'disassembly_pages', 'paper_repair', 'pressing', 'binding',
                  'damage_description', 'processing_notes', 'created_at']
        read_only_fields = ['id', 'created_at', 'restorer']


class ReviewRecordSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)
    conclusion_label = serializers.CharField(source='get_conclusion_display', read_only=True)

    class Meta:
        model = ReviewRecord
        fields = ['id', 'work_order', 'reviewer', 'reviewer_name',
                  'flatness', 'page_order_check', 'cover_status',
                  'conclusion', 'conclusion_label', 'rework_reason', 'created_at']
        read_only_fields = ['id', 'created_at', 'reviewer']


class StatusLogSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source='operator.get_full_name', read_only=True)
    from_status_label = serializers.SerializerMethodField()
    to_status_label = serializers.SerializerMethodField()

    class Meta:
        model = StatusLog
        fields = ['id', 'work_order', 'from_status', 'from_status_label',
                  'to_status', 'to_status_label', 'operator', 'operator_name',
                  'remark', 'created_at']

    def get_from_status_label(self, obj):
        if obj.from_status:
            return dict(WorkOrder.STATUS_CHOICES).get(obj.from_status, obj.from_status)
        return ''

    def get_to_status_label(self, obj):
        return dict(WorkOrder.STATUS_CHOICES).get(obj.to_status, obj.to_status)


class WorkOrderSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    book_no = serializers.CharField(source='book.book_no', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)
    paper_type_id = serializers.IntegerField(source='book.paper_type_id', read_only=True)
    paper_type_name = serializers.CharField(source='book.paper_type.name', read_only=True)
    workstation_name = serializers.CharField(source='workstation.name', read_only=True)
    restorer_name = serializers.CharField(source='restorer.get_full_name', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)
    processing_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = WorkOrder
        fields = [
            'id', 'book', 'book_no', 'book_title', 'paper_type_id', 'paper_type_name',
            'workstation', 'workstation_name', 'restorer', 'restorer_name',
            'reviewer', 'reviewer_name', 'review_interval_days',
            'status', 'status_label', 'received_at', 'started_at',
            'pressing_completed_at', 'review_due_at', 'completed_at',
            'suspended_at', 'rework_count', 'rework_reason',
            'processing_days', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'status',
                            'received_at', 'started_at', 'pressing_completed_at',
                            'review_due_at', 'completed_at', 'suspended_at',
                            'rework_count', 'rework_reason']


class WorkOrderDetailSerializer(WorkOrderSerializer):
    restoration_records = RestorationRecordSerializer(many=True, read_only=True)
    review_records = ReviewRecordSerializer(many=True, read_only=True)
    status_logs = StatusLogSerializer(many=True, read_only=True)

    class Meta(WorkOrderSerializer.Meta):
        fields = WorkOrderSerializer.Meta.fields + [
            'restoration_records', 'review_records', 'status_logs'
        ]


class WorkOrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = ['book', 'workstation', 'restorer', 'reviewer', 'review_interval_days']

    def validate(self, attrs):
        book_id = attrs.get('book').id
        if WorkOrder.has_active_order(book_id):
            raise serializers.ValidationError('该书册存在未结束的工单，无法创建新工单')
        return attrs
