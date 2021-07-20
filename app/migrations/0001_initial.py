# Generated by Django 3.2.5 on 2021-07-20 09:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_mysql.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('aname', models.CharField(max_length=25, verbose_name='活动名称')),
                ('ayear', models.IntegerField(default=2021, verbose_name='活动年份')),
                ('asemester', models.CharField(choices=[('Fall', 'Fall'), ('Spring', 'Spring'), ('Fall+Spring', 'Annual')], max_length=15, verbose_name='活动学期')),
                ('astart', models.DateTimeField(verbose_name='开始时间')),
                ('afinish', models.DateTimeField(verbose_name='结束时间')),
                ('acontent', models.CharField(max_length=225, verbose_name='活动内容')),
                ('QRcode', models.ImageField(blank=True, upload_to='QRcode/')),
                ('astatus', models.CharField(choices=[('审核中', 'Asta Pending'), ('报名中', 'Applying'), ('等待中', 'Waiting'), ('进行中', 'Processing'), ('已取消', 'Canceled'), ('已结束', 'Finish'), ('未通过', 'Unsucceed')], max_length=32, verbose_name='活动状态')),
                ('mutableYQ', models.BooleanField(default=False, verbose_name='是否可以调整价格')),
                ('YQPoint', django_mysql.models.ListCharField(models.IntegerField(default=0), default=[0], max_length=50, size=10)),
                ('Places', django_mysql.models.ListCharField(models.IntegerField(default=0), default=[0], max_length=50, size=10)),
                ('URL', models.URLField(blank=True, null=True, verbose_name='相关网址')),
            ],
        ),
        migrations.CreateModel(
            name='NaturalPerson',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pname', models.CharField(max_length=10, verbose_name='姓名')),
                ('pnickname', models.CharField(blank=True, max_length=20, null=True, verbose_name='昵称')),
                ('pgender', models.SmallIntegerField(blank=True, choices=[(0, '男'), (1, '女'), (2, '其它')], null=True, verbose_name='性别')),
                ('pemail', models.EmailField(blank=True, max_length=254, null=True, verbose_name='邮箱')),
                ('ptel', models.CharField(blank=True, max_length=20, null=True, verbose_name='电话')),
                ('pBio', models.TextField(default='还没有填写哦～', max_length=1024, verbose_name='自我介绍')),
                ('avatar', models.ImageField(blank=True, upload_to='avatar/')),
                ('firstTimeLogin', models.BooleanField(default=True)),
                ('QRcode', models.ImageField(blank=True, upload_to='QRcode/')),
                ('YQPoint', models.FloatField(default=0.0, verbose_name='元气值')),
                ('pclass', models.CharField(blank=True, max_length=5, null=True, verbose_name='班级')),
                ('pmajor', models.CharField(blank=True, max_length=25, null=True, verbose_name='专业')),
                ('pyear', models.CharField(blank=True, max_length=5, null=True, verbose_name='年级')),
                ('pdorm', models.CharField(blank=True, max_length=6, null=True, verbose_name='宿舍')),
                ('pstatus', models.SmallIntegerField(choices=[(0, 'Undergraduated'), (1, 'Graduated')], default=0, verbose_name='在校状态')),
                ('TypeID', models.SmallIntegerField(choices=[(0, 'Teacher'), (1, 'Student')], default=1, verbose_name='身份')),
                ('show_nickname', models.BooleanField(default=True)),
                ('show_gender', models.BooleanField(default=True)),
                ('show_email', models.BooleanField(default=False)),
                ('show_tel', models.BooleanField(default=False)),
                ('show_major', models.BooleanField(default=True)),
                ('show_dorm', models.BooleanField(default=False)),
                ('pid', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('oname', models.CharField(max_length=32, unique=True)),
                ('ostatus', models.BooleanField(default=False, verbose_name='激活状态')),
                ('YQPoint', models.FloatField(default=0.0, verbose_name='元气值')),
                ('ointroduction', models.TextField(blank=True, default='这里暂时没有介绍哦~', null=True, verbose_name='介绍')),
                ('avatar', models.ImageField(blank=True, upload_to='avatar/')),
                ('QRcode', models.ImageField(blank=True, upload_to='QRcode/')),
                ('firstTimeLogin', models.BooleanField(default=True)),
                ('oid', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='TransferRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.FloatField(default=0, verbose_name='转账元气值数量')),
                ('time', models.DateTimeField(auto_now_add=True, verbose_name='转账时间')),
                ('message', models.CharField(default='', max_length=255, verbose_name='备注信息')),
                ('tstatus', models.IntegerField(choices=[(0, 'Accepted'), (1, 'Waiting'), (2, 'Refused'), (3, 'Suspended')], default=1)),
                ('proposer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='proposer_id', to=settings.AUTH_USER_MODEL)),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipient_id', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '转账信息',
                'verbose_name_plural': '转账信息',
                'ordering': ['time'],
            },
        ),
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pos', models.IntegerField(default=0, verbose_name='职务等级')),
                ('in_year', models.IntegerField(default=2021, verbose_name='当前学年')),
                ('in_semester', models.CharField(choices=[('Fall', 'Fall'), ('Spring', 'Spring'), ('Fall+Spring', 'Annual')], default='Fall+Spring', max_length=15, verbose_name='当前学期')),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='org', to='app.organization')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='person', to='app.naturalperson', to_field='pid')),
            ],
        ),
        migrations.CreateModel(
            name='Paticipant',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('aid', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.activity')),
                ('pid', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.naturalperson')),
            ],
        ),
        migrations.CreateModel(
            name='OrganizationType',
            fields=[
                ('otype_id', models.SmallIntegerField(primary_key=True, serialize=False, unique=True, verbose_name='组织类型编号')),
                ('otype_name', models.CharField(max_length=25, verbose_name='组织类型名称')),
                ('otype_superior_id', models.SmallIntegerField(default=0, verbose_name='上级组织类型编号')),
                ('ojob_name_list', django_mysql.models.ListCharField(models.CharField(max_length=10), max_length=44, size=4)),
                ('oincharge', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='oincharge', to='app.naturalperson')),
            ],
        ),
        migrations.AddField(
            model_name='organization',
            name='otype',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.organizationtype'),
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheduler', models.CharField(max_length=25, verbose_name='上课时间')),
                ('classroom', models.CharField(max_length=25, verbose_name='上课地点')),
                ('evaluation_manner', models.CharField(max_length=225, verbose_name='考核方式')),
                ('education_plan', models.CharField(max_length=225, verbose_name='教学计划')),
                ('cid', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cid', to='app.organization')),
            ],
        ),
        migrations.AddField(
            model_name='activity',
            name='oid',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='actoid', to='app.organization', to_field='oid'),
        ),
    ]
