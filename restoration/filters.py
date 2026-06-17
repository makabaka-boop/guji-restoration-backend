import django_filters
from .models import WorkOrder, Book


class WorkOrderFilter(django_filters.FilterSet):
    book_no = django_filters.CharFilter(field_name='book__book_no', lookup_expr='icontains')
    paper_type = django_filters.NumberFilter(field_name='book__paper_type__id')
    work_station = django_filters.NumberFilter(field_name='work_station__id')
    status = django_filters.CharFilter(field_name='status')
    responsible_person = django_filters.NumberFilter(field_name='responsible_person__id')
    restorer = django_filters.NumberFilter(field_name='restorer__id')
    start_date = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    end_date = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte')

    class Meta:
        model = WorkOrder
        fields = ['book_no', 'paper_type', 'work_station', 'status', 'responsible_person', 'restorer']


class BookFilter(django_filters.FilterSet):
    book_no = django_filters.CharFilter(field_name='book_no', lookup_expr='icontains')
    title = django_filters.CharFilter(field_name='title', lookup_expr='icontains')
    paper_type = django_filters.NumberFilter(field_name='paper_type__id')
    binding_type = django_filters.NumberFilter(field_name='binding_type__id')

    class Meta:
        model = Book
        fields = ['book_no', 'title', 'paper_type', 'binding_type']
