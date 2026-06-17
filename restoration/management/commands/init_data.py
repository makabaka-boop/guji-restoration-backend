from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from restoration.models import (
    PaperType, BindingType, WorkStation, ResponsiblePerson, Book
)

User = get_user_model()


class Command(BaseCommand):
    help = '初始化系统基础数据和测试账号'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化数据...')

        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                password='admin123',
                role=User.ROLE_ADMIN,
                email='admin@example.com',
                first_name='系统',
                last_name='管理员'
            )
            self.stdout.write('  - 创建管理员账号: admin / admin123')

        if not User.objects.filter(username='restorer').exists():
            User.objects.create_user(
                username='restorer',
                password='restorer123',
                role=User.ROLE_RESTORER,
                email='restorer@example.com',
                first_name='张',
                last_name='修护师'
            )
            self.stdout.write('  - 创建修护师账号: restorer / restorer123')

        if not User.objects.filter(username='reviewer').exists():
            User.objects.create_user(
                username='reviewer',
                password='reviewer123',
                role=User.ROLE_REVIEWER,
                email='reviewer@example.com',
                first_name='李',
                last_name='复核员'
            )
            self.stdout.write('  - 创建复核员账号: reviewer / reviewer123')

        paper_types = ['宣纸', '毛边纸', '连史纸', '皮纸', '竹纸']
        for name in paper_types:
            PaperType.objects.get_or_create(name=name)
        self.stdout.write(f'  - 初始化 {len(paper_types)} 种纸张类型')

        binding_types = ['线装', '包背装', '蝴蝶装', '经折装', '卷轴装']
        for name in binding_types:
            BindingType.objects.get_or_create(name=name)
        self.stdout.write(f'  - 初始化 {len(binding_types)} 种装订形式')

        stations = [
            ('WS001', '修护一台', '主修护工作台'),
            ('WS002', '修护二台', '主修护工作台'),
            ('WS003', '压平台', '压平专用台位'),
            ('WS004', '复核台', '复核专用台位'),
        ]
        for code, name, desc in stations:
            WorkStation.objects.get_or_create(
                code=code,
                defaults={'name': name, 'description': desc}
            )
        self.stdout.write(f'  - 初始化 {len(stations)} 个处理台位')

        persons = [
            ('EMP001', '王师傅', '修护部', '13800138001'),
            ('EMP002', '赵师傅', '修护部', '13800138002'),
            ('EMP003', '钱主任', '质量部', '13800138003'),
        ]
        for eid, name, dept, phone in persons:
            ResponsiblePerson.objects.get_or_create(
                employee_id=eid,
                defaults={'name': name, 'department': dept, 'phone': phone}
            )
        self.stdout.write(f'  - 初始化 {len(persons)} 位责任人')

        if Book.objects.count() == 0:
            pt1 = PaperType.objects.get(name='宣纸')
            bt1 = BindingType.objects.get(name='线装')
            books = [
                ('BK001', '论语', pt1, bt1, 120, '儒家经典著作'),
                ('BK002', '孟子', pt1, bt1, 100, '儒家经典著作'),
                ('BK003', '道德经', PaperType.objects.get(name='皮纸'), bt1, 80, '道家经典'),
            ]
            for bno, title, pt, bt, pc, desc in books:
                Book.objects.create(
                    book_no=bno, title=title, paper_type=pt,
                    binding_type=bt, page_count=pc, description=desc
                )
            self.stdout.write(f'  - 初始化 {len(books)} 本书册')

        self.stdout.write('初始化完成！')
