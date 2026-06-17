from django.core.management.base import BaseCommand
from django.utils import timezone
from restoration.models import (
    User, PaperType, BindingType, Station, Book, WorkOrder,
    RestorationRecord, ReviewRecord, StatusLog,
    ROLE_ADMIN, ROLE_RESTORER, ROLE_REVIEWER,
    STATUS_PENDING, STATUS_PROCESSING, STATUS_PENDING_PRESS,
    STATUS_PENDING_REVIEW, STATUS_REWORKING, STATUS_STORABLE, STATUS_PAUSED,
    REVIEW_PASS, REVIEW_REWORK,
)


class Command(BaseCommand):
    help = '初始化测试数据'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化数据...')

        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'role': ROLE_ADMIN,
                'email': 'admin@example.com',
                'first_name': '系统',
                'last_name': '管理员',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin_user.set_password('admin123')
        admin_user.save()

        restorer1, _ = User.objects.get_or_create(
            username='xiufu1',
            defaults={
                'role': ROLE_RESTORER,
                'email': 'xiufu1@example.com',
                'first_name': '张',
                'last_name': '修护',
            }
        )
        restorer1.set_password('xiufu123')
        restorer1.save()

        restorer2, _ = User.objects.get_or_create(
            username='xiufu2',
            defaults={
                'role': ROLE_RESTORER,
                'email': 'xiufu2@example.com',
                'first_name': '李',
                'last_name': '修护',
            }
        )
        restorer2.set_password('xiufu123')
        restorer2.save()

        reviewer1, _ = User.objects.get_or_create(
            username='fuhe1',
            defaults={
                'role': ROLE_REVIEWER,
                'email': 'fuhe1@example.com',
                'first_name': '王',
                'last_name': '复核',
            }
        )
        reviewer1.set_password('fuhe123')
        reviewer1.save()

        reviewer2, _ = User.objects.get_or_create(
            username='fuhe2',
            defaults={
                'role': ROLE_REVIEWER,
                'email': 'fuhe2@example.com',
                'first_name': '赵',
                'last_name': '复核',
            }
        )
        reviewer2.set_password('fuhe123')
        reviewer2.save()

        paper_types_data = ['宣纸', '毛边纸', '连史纸', '皮纸', '竹纸']
        paper_types = {}
        for name in paper_types_data:
            pt, _ = PaperType.objects.get_or_create(name=name)
            paper_types[name] = pt

        binding_types_data = ['线装', '平装', '精装', '经折装', '蝴蝶装']
        binding_types = {}
        for name in binding_types_data:
            bt, _ = BindingType.objects.get_or_create(name=name)
            binding_types[name] = bt

        stations_data = ['台位A', '台位B', '台位C', '压平台']
        stations = {}
        for name in stations_data:
            st, _ = Station.objects.get_or_create(name=name)
            stations[name] = st

        books_data = [
            ('GJ-001', '宣纸', '线装', '台位A', restorer1, 7, '《永乐大典》卷一'),
            ('GJ-002', '毛边纸', '平装', '台位B', restorer2, 7, '《四库全书》册三'),
            ('GJ-003', '连史纸', '线装', '台位A', restorer1, 5, '《史记》孤本'),
            ('GJ-004', '皮纸', '经折装', '台位C', restorer2, 10, '佛经卷轴'),
            ('GJ-005', '竹纸', '蝴蝶装', '台位B', restorer1, 7, '《本草纲目》刻本'),
            ('GJ-006', '宣纸', '线装', '台位A', restorer2, 7, '《唐诗三百首》抄本'),
        ]

        for bn, pt_name, bt_name, st_name, restorer, interval, desc in books_data:
            book, created = Book.objects.get_or_create(
                book_number=bn,
                defaults={
                    'paper_type': paper_types[pt_name],
                    'binding_type': binding_types[bt_name],
                    'default_station': stations[st_name],
                    'default_restorer': restorer,
                    'review_interval_days': interval,
                    'description': desc,
                }
            )
            if created:
                self.stdout.write(f'  创建书册: {bn}')

        if WorkOrder.objects.count() == 0:
            self.stdout.write('  创建示例工单...')
            self._create_sample_orders(paper_types, binding_types, stations, restorer1, restorer2, reviewer1)

        self.stdout.write(self.style.SUCCESS('数据初始化完成!'))
        self.stdout.write('测试账号:')
        self.stdout.write('  管理员: admin / admin123')
        self.stdout.write('  修护师1: xiufu1 / xiufu123')
        self.stdout.write('  修护师2: xiufu2 / xiufu123')
        self.stdout.write('  复核员1: fuhe1 / fuhe123')
        self.stdout.write('  复核员2: fuhe2 / fuhe123')

    def _create_sample_orders(self, paper_types, binding_types, stations, restorer1, restorer2, reviewer1):
        now = timezone.now()

        book1 = Book.objects.get(book_number='GJ-001')
        order1 = WorkOrder.objects.create(
            book=book1,
            order_no='WO20260615000001',
            status=STATUS_STORABLE,
            station=stations['台位A'],
            restorer=restorer1,
            review_interval_days=7,
            received_at=now - timezone.timedelta(days=10),
            processing_started_at=now - timezone.timedelta(days=9, hours=8),
            press_started_at=now - timezone.timedelta(days=6),
            press_completed_at=now - timezone.timedelta(days=5),
            review_due_at=now - timezone.timedelta(days=3),
            review_completed_at=now - timezone.timedelta(days=4),
            completed_at=now - timezone.timedelta(days=4),
            rework_count=0,
        )
        RestorationRecord.objects.create(
            work_order=order1, restorer=restorer1,
            disassembly_done=True, disassembly_note='拆页顺利，共120页',
            paper_repair_done=True, paper_repair_note='修补破损页面15处',
            press_done=True, press_level='medium', press_duration_hours=48,
            press_note='压平效果良好',
            binding_done=True, binding_note='重新装订线装',
            damage_description='书脊破损，部分页面虫蛀',
            handling_note='整体状况良好',
            created_at=now - timezone.timedelta(days=8),
        )
        ReviewRecord.objects.create(
            work_order=order1, reviewer=reviewer1,
            flatness='good', flatness_note='平整度良好',
            page_order_correct=True, page_order_note='页序正确',
            cover_status='minor_damage', cover_note='封面有轻微磨损',
            conclusion=REVIEW_PASS, review_note='整体合格',
            created_at=now - timezone.timedelta(days=4),
        )
        StatusLog.objects.create(
            work_order=order1, to_status=STATUS_PENDING,
            operator=restorer1, remark='工单创建',
            created_at=now - timezone.timedelta(days=10),
        )
        StatusLog.objects.create(
            work_order=order1, from_status=STATUS_PENDING,
            to_status=STATUS_PROCESSING, operator=restorer1,
            remark='接收工单',
            created_at=now - timezone.timedelta(days=9, hours=8),
        )
        StatusLog.objects.create(
            work_order=order1, from_status=STATUS_PROCESSING,
            to_status=STATUS_PENDING_REVIEW, operator=restorer1,
            remark='修护完成，提交复核',
            created_at=now - timezone.timedelta(days=5),
        )
        StatusLog.objects.create(
            work_order=order1, from_status=STATUS_PENDING_REVIEW,
            to_status=STATUS_STORABLE, operator=reviewer1,
            remark='复核通过，可入库',
            created_at=now - timezone.timedelta(days=4),
        )

        book2 = Book.objects.get(book_number='GJ-002')
        order2 = WorkOrder.objects.create(
            book=book2,
            order_no='WO20260616000002',
            status=STATUS_PROCESSING,
            station=stations['台位B'],
            restorer=restorer2,
            review_interval_days=7,
            received_at=now - timezone.timedelta(days=2),
            processing_started_at=now - timezone.timedelta(days=2),
            rework_count=0,
        )
        RestorationRecord.objects.create(
            work_order=order2, restorer=restorer2,
            disassembly_done=True, disassembly_note='拆页完成',
            paper_repair_done=True, paper_repair_note='补纸完成',
            press_done=False, binding_done=False,
            damage_description='书页边缘磨损',
            handling_note='继续处理中',
        )
        StatusLog.objects.create(
            work_order=order2, to_status=STATUS_PENDING,
            operator=restorer1, remark='工单创建',
            created_at=now - timezone.timedelta(days=3),
        )
        StatusLog.objects.create(
            work_order=order2, from_status=STATUS_PENDING,
            to_status=STATUS_PROCESSING, operator=restorer2,
            remark='接收工单',
            created_at=now - timezone.timedelta(days=2),
        )

        book3 = Book.objects.get(book_number='GJ-003')
        order3 = WorkOrder.objects.create(
            book=book3,
            order_no='WO20260610000003',
            status=STATUS_PENDING_REVIEW,
            station=stations['台位A'],
            restorer=restorer1,
            review_interval_days=5,
            received_at=now - timezone.timedelta(days=8),
            processing_started_at=now - timezone.timedelta(days=7),
            press_started_at=now - timezone.timedelta(days=5),
            press_completed_at=now - timezone.timedelta(days=4),
            review_due_at=now - timezone.timedelta(days=1),
            rework_count=1,
        )
        RestorationRecord.objects.create(
            work_order=order3, restorer=restorer1,
            disassembly_done=True, paper_repair_done=True,
            press_done=True, press_level='heavy', press_duration_hours=72,
            binding_done=True,
            damage_description='严重虫蛀',
            handling_note='第一次修护后返工',
        )
        ReviewRecord.objects.create(
            work_order=order3, reviewer=reviewer1,
            flatness='fair', flatness_note='平整度一般',
            page_order_correct=False, page_order_note='第30页顺序有误',
            cover_status='minor_damage',
            conclusion=REVIEW_REWORK, rework_reason='页序错误，平整度不够',
            review_note='需返工调整',
            created_at=now - timezone.timedelta(days=3),
        )
        RestorationRecord.objects.create(
            work_order=order3, restorer=restorer1,
            disassembly_done=True, paper_repair_done=True,
            press_done=True, press_level='heavy', press_duration_hours=96,
            binding_done=True,
            damage_description='返工修复',
            handling_note='已调整页序，重新压平',
        )

        book4 = Book.objects.get(book_number='GJ-004')
        WorkOrder.objects.create(
            book=book4,
            order_no='WO20260617000004',
            status=STATUS_PENDING,
            station=stations['台位C'],
            restorer=restorer2,
            review_interval_days=10,
            rework_count=0,
        )

        book5 = Book.objects.get(book_number='GJ-005')
        order5 = WorkOrder.objects.create(
            book=book5,
            order_no='WO20260612000005',
            status=STATUS_PENDING_PRESS,
            station=stations['台位B'],
            restorer=restorer1,
            review_interval_days=7,
            received_at=now - timezone.timedelta(days=6),
            processing_started_at=now - timezone.timedelta(days=5),
            press_started_at=now - timezone.timedelta(days=4),
            press_completed_at=now - timezone.timedelta(days=3),
            rework_count=0,
        )
        RestorationRecord.objects.create(
            work_order=order5, restorer=restorer1,
            disassembly_done=True, paper_repair_done=True,
            press_done=True, press_level='medium', press_duration_hours=24,
            binding_done=False,
            damage_description='封面破损',
            handling_note='压平完成，待装订',
        )

        book6 = Book.objects.get(book_number='GJ-006')
        order6 = WorkOrder.objects.create(
            book=book6,
            order_no='WO20260614000006',
            status=STATUS_REWORKING,
            station=stations['台位A'],
            restorer=restorer2,
            review_interval_days=7,
            received_at=now - timezone.timedelta(days=5),
            processing_started_at=now - timezone.timedelta(days=4),
            press_completed_at=now - timezone.timedelta(days=2),
            review_due_at=now + timezone.timedelta(days=5),
            review_completed_at=now - timezone.timedelta(days=1),
            rework_count=1,
        )
        ReviewRecord.objects.create(
            work_order=order6, reviewer=reviewer1,
            flatness='poor', flatness_note='平整度差，有褶皱',
            page_order_correct=True,
            cover_status='major_damage', cover_note='封面破损严重',
            conclusion=REVIEW_REWORK, rework_reason='平整度差，封面破损',
            review_note='需重新处理',
            created_at=now - timezone.timedelta(days=1),
        )
