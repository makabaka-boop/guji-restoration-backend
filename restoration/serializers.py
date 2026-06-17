from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    PaperType, BindingType, WorkStation, ResponsiblePerson,
    Book, WorkOrder, RepairRecord, ReviewRecord
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'role', 'role_name', 'email', 'phone', 'first_name', 'last_name']
        read_only_fields = ['id', 'username']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'role', 'email', 'phone', 'first_name', 'last_name']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class PaperTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperType
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class BindingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BindingType
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkStation
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ResponsiblePersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponsiblePerson
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class BookSerializer(serializers.ModelSerializer):
    paper_type_name = serializers.CharField(source='paper_type.name', read_only=True)
    binding_type_name = serializers.CharField(source='binding_type.name', read_only=True)
    current_status = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'book_no', 'title', 'paper_type', 'paper_type_name',
            'binding_type', 'binding_type_name', 'page_count', 'description',
            'created_at', 'updated_at', 'current_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'current_status']

    def get_current_status(self, obj):
        current = obj.current_work_order
        if current:
            return {
                'order_no': current.order_no,
                'status': current.status,
                'status_name': current.get_status_display()
            }
        return None


class WorkOrderListSerializer(serializers.ModelSerializer):
    book_no = serializers.CharField(source='book.book_no', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)
    paper_type_name = serializers.CharField(source='book.paper_type.name', read_only=True)
    work_station_code = serializers.CharField(source='work_station.code', read_only=True)
    work_station_name = serializers.CharField(source='work_station.name', read_only=True)
    responsible_person_name = serializers.CharField(source='responsible_person.name', read_only=True)
    restorer_name = serializers.CharField(source='restorer.username', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True, allow_null=True)
    status_name = serializers.CharField(source='get_status_display', read_only=True)
    process_duration_hours = serializers.FloatField(read_only=True)

    class Meta:
        model = WorkOrder
        fields = [
            'id', 'order_no', 'book', 'book_no', 'book_title', 'paper_type_name',
            'work_station', 'work_station_code', 'work_station_name',
            'responsible_person', 'responsible_person_name',
            'restorer', 'restorer_name', 'reviewer', 'reviewer_name',
            'status', 'status_name', 'review_interval_hours',
            'rework_count', 'process_duration_hours',
            'receive_time', 'start_time', 'press_start_time',
            'press_complete_time', 'review_submit_time', 'complete_time',
            'created_at', 'updated_at'
        ]


class WorkOrderDetailSerializer(WorkOrderListSerializer):
    repair_records = serializers.SerializerMethodField()
    review_records = serializers.SerializerMethodField()

    class Meta(WorkOrderListSerializer.Meta):
        fields = WorkOrderListSerializer.Meta.fields + [
            'damage_description', 'process_remark', 'repair_records', 'review_records'
        ]

    def get_repair_records(self, obj):
        records = obj.repair_records.all()
        return RepairRecordSerializer(records, many=True).data

    def get_review_records(self, obj):
        records = obj.review_records.all()
        return ReviewRecordSerializer(records, many=True).data


class WorkOrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = [
            'book', 'work_station', 'responsible_person', 'restorer',
            'reviewer', 'review_interval_hours', 'damage_description'
        ]

    def validate_book(self, value):
        active_orders = WorkOrder.objects.filter(
            book=value, status__in=WorkOrder.ACTIVE_STATUSES
        )
        if active_orders.exists():
            raise serializers.ValidationError('该书册存在未结束的工单，无法创建新工单')
        return value

    def create(self, validated_data):
        from django.utils import timezone
        import uuid
        order_no = f'WO{timezone.now().strftime("%Y%m%d%H%M%S")}{uuid.uuid4().hex[:4].upper()}'
        validated_data['order_no'] = order_no
        return super().create(validated_data)


class RepairRecordSerializer(serializers.ModelSerializer):
    restorer_name = serializers.CharField(source='restorer.username', read_only=True)

    class Meta:
        model = RepairRecord
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'restorer']


class RepairSubmitSerializer(serializers.Serializer):
    has_page_separation = serializers.BooleanField(default=False)
    has_paper_repair = serializers.BooleanField(default=False)
    has_pressing = serializers.BooleanField(default=False)
    has_binding = serializers.BooleanField(default=False)
    damage_description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    process_remark = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ReviewRecordSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True)
    flatness_name = serializers.CharField(source='get_flatness_display', read_only=True)
    page_order_name = serializers.CharField(source='get_page_order_display', read_only=True)
    cover_status_name = serializers.CharField(source='get_cover_status_display', read_only=True)
    conclusion_name = serializers.CharField(source='get_conclusion_display', read_only=True)

    class Meta:
        model = ReviewRecord
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'reviewer', 'work_order']


class ReviewSubmitSerializer(serializers.Serializer):
    flatness = serializers.ChoiceField(choices=ReviewRecord.FLATNESS_CHOICES)
    page_order = serializers.ChoiceField(choices=ReviewRecord.PAGE_ORDER_CHOICES)
    cover_status = serializers.ChoiceField(choices=ReviewRecord.COVER_CHOICES)
    conclusion = serializers.ChoiceField(choices=ReviewRecord.RESULT_CHOICES)
    rework_reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    review_remark = serializers.CharField(required=False, allow_blank=True, allow_null=True)
