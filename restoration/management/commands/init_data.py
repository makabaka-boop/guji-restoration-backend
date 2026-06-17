from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from restoration.models import PaperType, BindingType, Workstation, Book

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialize system with default users and base data'

    def handle(self, *args, **options):
        self.stdout.write('Creating default users...')

        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'first_name': '系统',
                'last_name': '管理员',
                'email': 'admin@example.com',
                'role': User.ROLE_ADMIN,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123456')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Created admin user: admin / admin123456'))
        else:
            self.stdout.write('Admin user already exists')

        restorer1, created = User.objects.get_or_create(
            username='restorer1',
            defaults={
                'first_name': '张',
                'last_name': '修护',
                'email': 'restorer1@example.com',
                'role': User.ROLE_RESTORER,
            }
        )
        if created:
            restorer1.set_password('restorer123')
            restorer1.save()
            self.stdout.write(self.style.SUCCESS('Created restorer: restorer1 / restorer123'))

        restorer2, created = User.objects.get_or_create(
            username='restorer2',
            defaults={
                'first_name': '李',
                'last_name': '修护',
                'email': 'restorer2@example.com',
                'role': User.ROLE_RESTORER,
            }
        )
        if created:
            restorer2.set_password('restorer123')
            restorer2.save()
            self.stdout.write(self.style.SUCCESS('Created restorer: restorer2 / restorer123'))

        reviewer1, created = User.objects.get_or_create(
            username='reviewer1',
            defaults={
                'first_name': '王',
                'last_name': '复核',
                'email': 'reviewer1@example.com',
                'role': User.ROLE_REVIEWER,
            }
        )
        if created:
            reviewer1.set_password('reviewer123')
            reviewer1.save()
            self.stdout.write(self.style.SUCCESS('Created reviewer: reviewer1 / reviewer123'))

        reviewer2, created = User.objects.get_or_create(
            username='reviewer2',
            defaults={
                'first_name': '赵',
                'last_name': '复核',
                'email': 'reviewer2@example.com',
                'role': User.ROLE_REVIEWER,
            }
        )
        if created:
            reviewer2.set_password('reviewer123')
            reviewer2.save()
            self.stdout.write(self.style.SUCCESS('Created reviewer: reviewer2 / reviewer123'))

        self.stdout.write('Creating base data...')

        paper_types = ['宣纸', '毛边纸', '连史纸', '皮纸', '竹纸']
        for name in paper_types:
            PaperType.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS(f'Created {len(paper_types)} paper types'))

        binding_types = ['线装', '包背装', '蝴蝶装', '经折装', '旋风装']
        for name in binding_types:
            BindingType.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS(f'Created {len(binding_types)} binding types'))

        workstations = ['1号台', '2号台', '3号台', '压平台A', '压平台B']
        for name in workstations:
            Workstation.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS(f'Created {len(workstations)} workstations'))

        if not Book.objects.exists():
            pt1 = PaperType.objects.first()
            bt1 = BindingType.objects.first()
            sample_books = [
                ('GJ-001', '永乐大典·卷一', 200, '明永乐年间手抄本'),
                ('GJ-002', '四库全书·经部', 350, '清乾隆年间抄本'),
                ('GJ-003', '本草纲目', 180, '明万历年间刻本'),
                ('GJ-004', '红楼梦·庚辰本', 220, '清乾隆年间抄本'),
                ('GJ-005', '史记·三家注', 280, '宋刻本影印'),
            ]
            for book_no, title, pages, desc in sample_books:
                Book.objects.get_or_create(
                    book_no=book_no,
                    defaults={
                        'title': title,
                        'paper_type': pt1,
                        'binding_type': bt1,
                        'total_pages': pages,
                        'description': desc,
                    }
                )
            self.stdout.write(self.style.SUCCESS(f'Created {len(sample_books)} sample books'))

        self.stdout.write(self.style.SUCCESS('Initialization completed!'))
