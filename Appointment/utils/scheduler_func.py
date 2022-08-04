# YWolfeee:
# 本py文件保留所有需要与scheduler交互的函数。
from Appointment import *

from Appointment.models import Participant, Room, Appoint,LongTermAppoint, College_Announcement
from django.http import JsonResponse, HttpResponse  # Json响应
from django.shortcuts import render, redirect  # 网页render & redirect
from django.urls import reverse
from datetime import datetime, timedelta, timezone, time, date
from django.db import transaction  # 原子化更改数据库
import Appointment.utils.utils as utils
import Appointment.utils.web_func as web_func
from Appointment.utils.identity import get_participant

'''
YWolfeee:
scheduler_func.py是所有和scheduler定时任务发生交互的函数集合。
本py文件中的所有函数，或者发起了一个scheduler任务，或者删除了一个scheduler任务。
这些函数大多对应预约的开始、结束，微信的定时发送等。
如果需要实现新的函数，建议先详细阅读本py中其他函数的实现方式。
'''

from boottest.scheduler import scheduler


# 每周清除预约的程序，会写入logstore中
def clear_appointments():
    if GLOBAL_INFO.delete_appoint_weekly:   # 是否清除一周之前的预约
        appoints_to_delete = Appoint.objects.filter(
            Afinish__lte=datetime.now()-timedelta(days=7))
        try:
            # with transaction.atomic(): //不采取原子操作
            utils.write_before_delete(appoints_to_delete)  # 删除之前写在记录内
            appoints_to_delete.delete()
        except Exception as e:
            utils.operation_writer(SYSTEM_LOG, "定时删除任务出现错误: "+str(e),
                            "scheduler_func.clear_appointments", "Problem")

        # 写入日志
        utils.operation_writer(SYSTEM_LOG, "定时删除任务成功", "scheduler_func.clear_appointments")


def set_scheduler(appoint):
    '''不负责发送微信,不处理已经结束的预约,不处理始末逆序的预约,可以任何时间点调用,应该不报错'''
    # --- written by pht: 统一设置预约定时任务 --- #
    start = appoint.Astart
    finish = appoint.Afinish
    current_time = datetime.now() + timedelta(seconds=5)
    if finish < start:          # 开始晚于结束，预约不合规
        utils.operation_writer(
                                SYSTEM_LOG,
                                f'预约{appoint.Aid}时间为{start}<->{finish}，未能设置定时任务',
                                'scheduler_func.set_scheduler',
                                'Error'
                                )
        return False            # 直接返回，预约不需要设置
    if finish < current_time:   # 预约已经结束
        utils.operation_writer(
                                SYSTEM_LOG,
                                f'预约{appoint.Aid}在设置定时任务时已经结束',
                                'scheduler_func.set_scheduler',
                                'Error'
                                )
        return False            # 直接返回，预约不需要设置
    has_started = start < current_time
    if has_started:             # 临时预约或特殊情况下设置任务时预约可能已经开始
        start = current_time    # 改为立刻执行
    # --- written end (2021.8.31) --- #

    # written by dyh: 在Astart将状态变为PROCESSING
    if not (has_started and appoint.Astatus == Appoint.Status.PROCESSING):
        scheduler.add_job(web_func.startAppoint,
                            args=[appoint.Aid],
                            id=f'{appoint.Aid}_start',
                            replace_existing=True,
                            next_run_time=start)

    # write by cdf start2  # 添加定时任务：finish
    scheduler.add_job(web_func.finishAppoint,
                        args=[appoint.Aid],
                        id=f'{appoint.Aid}_finish',
                        replace_existing=True,
                        next_run_time=finish)
    return True


def cancel_scheduler(appoint_or_aid, status_code=None):  # models.py中使用
    '''
    status_code合法时且非空时,记录未找到的定时任务,不抛出异常
    逻辑是finish标识预约是否终止,未终止时才取消其它定时任务
    '''
    # --- modify by pht: 统一设置预约定时任务 --- #
    if isinstance(appoint_or_aid, Appoint):
        aid = appoint_or_aid.Aid
    else:
        aid = appoint_or_aid
    try:
        scheduler.remove_job(f'{aid}_finish')
        try:
            scheduler.remove_job(f'{aid}_start')
        except:
            if status_code: utils.operation_writer(
                SYSTEM_LOG,
                f"预约{aid}取消时未发现开始计时器",
                'scheduler_func.cancel_scheduler',
                status_code)
        try:
            scheduler.remove_job(f'{aid}_start_wechat')
        except:
            if status_code: utils.operation_writer(
                SYSTEM_LOG,
                f"预约{aid}取消时未发现wechat计时器，但也可能本来就没有",
                'scheduler_func.cancel_scheduler')  # 微信消息发送大概率不存在
        return True
    except:
        if status_code: utils.operation_writer(
            SYSTEM_LOG,
            f"预约{aid}取消时未发现计时器",
            'scheduler_func.cancel_scheduler',
            status_code)
        return False


def set_appoint_wechat(appoint: Appoint, message_type: str, *extra_infos,
                       students_id=None, admin=None,
                       id=None, job_time=None):
    '''设置预约的微信提醒，默认发给所有参与者'''
    if students_id is None:
        # 先准备发送人
        students_id = list(appoint.students.values_list('Sid', flat=True))

    # 默认立刻发送
    if job_time is None:
        job_time = datetime.now() + timedelta(seconds=5)

    # 添加定时任务的关键字参数
    add_job_kws = dict(replace_existing=True, next_run_time=job_time)
    if id is not None:
        add_job_kws.update(id=id)
    scheduler.add_job(utils.send_wechat_message,
                      args=[
                          students_id,
                          appoint.Astart,
                          appoint.Room,
                          message_type,
                          appoint.major_student.name,
                          appoint.Ausage,
                          appoint.Aannouncement,
                          appoint.Anon_yp_num + appoint.Ayp_num,
                          *extra_infos[:1],
                      ],
                      **add_job_kws)


def set_cancel_wechat(appoint: Appoint, students_id=None):
    '''取消预约的微信提醒，默认发给所有参与者'''
    set_appoint_wechat(
        appoint, 'cancel',
        students_id=students_id, id=f'{appoint.Aid}_cancel_wechat')


# added by pht: 8.31
def set_start_wechat(appoint, students_id=None, notify_create=True):
    '''将预约成功和开始前的提醒定时发送给微信'''
    if students_id is None:
        students_id = list(appoint.students.values_list('Sid', flat=True))
    # write by cdf end2
    # modify by pht: 如果已经开始，非临时预约记录log
    if datetime.now() >= appoint.Astart:
        # add by lhw : 临时预约 #
        if appoint.Atemp_flag == True:
            set_appoint_wechat(
                appoint, 'temp_appointment',
                students_id=students_id, id=f'{appoint.Aid}_new_wechat')
        else:
            utils.operation_writer(SYSTEM_LOG,
                                   f'预约{appoint.Aid}尝试发送给微信时已经开始，且并非临时预约',
                                   'scheduler_func.set_start_wechat', 'Problem')
            return False
    elif datetime.now() <= appoint.Astart - timedelta(minutes=15):
        # 距离预约开始还有15分钟以上，提醒有新预约&定时任务
        if notify_create:  # 只有在非长线预约中才添加这个job
            set_appoint_wechat(
                appoint, 'new',
                students_id=students_id, id=f'{appoint.Aid}_new_wechat')
        set_appoint_wechat(
            appoint, 'start',
            students_id=students_id, id=f'{appoint.Aid}_start_wechat',
            job_time=appoint.Astart - timedelta(minutes=15))
    else:
        # 距离预约开始还有不到15分钟，提醒有新预约并且马上开始
        set_appoint_wechat(
            appoint, 'new&start',
            students_id=students_id, id=f'{appoint.Aid}_new_wechat')
    return True


def set_longterm_wechat(appoint: Appoint, students_id=None, infos='', admin=False):
    '''长期预约的微信提醒，默认发给所有参与者'''
    set_appoint_wechat(
        appoint, 'longterm_created_admin' if admin else 'longterm_created', infos,
        students_id=students_id, id=f'{appoint.Aid}_longterm_created_wechat')


def set_longterm_reviewing_wechat(longterm_appoint:LongTermAppoint):
    '''长期预约的审核老师通知提醒，发送给对应的审核老师'''
    # TODO: 待优化
    review_url = GLOBAL_INFO.this_url.rstrip("/") + "/review?Lid=" + longterm_appoint.id
    
    def get_audit_teachers(applicant:Participant) -> list [str]:
        raise NotImplementedError()

    teachers_id = get_audit_teachers(longterm_appoint.applicant)
    utils.send_wechat_message(
        message_type="longterm_reviewing",
        stuid_list=teachers_id,
        url=review_url,
        start_time=longterm_appoint.appoint.Astart,
        room=longterm_appoint.appoint.Room,
        usage=longterm_appoint.appoint.Ausage,
        major_student=longterm_appoint.applicant,
    )

def set_longterm_reviewed_wechat(longterm_appoint:LongTermAppoint, action:str="" ):
    '''长期预约的审核状态变更通知提醒，发送给发起预约的组织和负责人'''
    # TODO: 待优化
    if action in  ["approved","rejected"]:
        utils.send_wechat_message(
            message_type="longterm_" + action,
            stuid_list=[longterm_appoint.applicant.get_id()],
            room=longterm_appoint.appoint.Room,
            usage=longterm_appoint.appoint.Ausage,
            major_student=longterm_appoint.applicant,
        )

# 过渡，待废弃
def _success(data):
    return JsonResponse({'data': data}, status=200)

def _error(msg: str, detail=None):
    content = dict(message=msg)
    if detail is not None:
        content.update(detail=str(detail))
    return JsonResponse({'statusInfo': content}, status=400)

def addAppoint(contents: dict,
               type: Appoint.Type = Appoint.Type.NORMAL,
               check_contents: bool = True,
               notify_create: bool = True) -> JsonResponse:
    '''
    创建一个预约，检查各种条件，屎山函数

    :param contents: 屎山，只知道Sid: arg for `get_participant`
    :type contents: dict
    :param type: 预约类型, defaults to Appoint.Type.NORMAL
    :type type: Appoint.Type, optional
    :param check_contents: 是否检查参数，暂未启用, defaults to True
    :type check_contents: bool, optional
    :param notify_create: 是否通知参与者创建了新预约, defaults to True
    :type notify_create: bool, optional
    :return: 屎山
    :rtype: JsonResponse
    '''

    # 检查是否为临时预约 add by lhw (2021.7.13)
    # TODO: remove temp flag
    contents.setdefault('Atemp_flag', False)
    # 首先检查房间是否存在
    try:
        room = Room.objects.get(Rid=contents['Rid'])
        assert room.Rstatus == Room.Status.PERMITTED, 'room service suspended!'
    except Exception as e:
        return _error('房间不可预约，请更换房间！', e)
    # 再检查学号对不对
    students_id = contents['students']  # 存下学号列表
    students = Participant.objects.filter(Sid__in=students_id)  # 获取学生
    try:
        assert students.count() == len(students_id), "students repeat or don't exists"
    except Exception as e:
        return _error('预约人信息有误，请检查后重新发起预约！', e)

    # 检查人员信息
    try:
        # ---- modify by lhw: 加入考虑临时预约的情况 ---- #
        current_time = datetime.now()   # 获取当前时间，只获取一次，防止多次获取得到不同时间
        if current_time.date() != contents['Astart'].date():    # 若不为当天
            real_min = room.Rmin
        elif contents['Atemp_flag']:                            # 临时预约，放宽限制
            real_min = min(room.Rmin, GLOBAL_INFO.temporary_min)
        else:                                                   # 当天预约，放宽限制
            real_min = min(room.Rmin, GLOBAL_INFO.today_min)
        # ----- modify end : 2021.7.10 ----- #

        assert len(students) + contents[
            'non_yp_num'] >= real_min, f'at least {room.Rmin} students'
    except Exception as e:
        return _error('使用总人数需达到房间最小人数！', e)
    # 检查外院人数是否过多
    try:
        # assert len(
        #    students) >= contents['non_yp_num'], f"too much non-yp students!"
        assert 2 * len(students) >= real_min, f"too little yp students!"
    except Exception as e:
        return _error('院内使用人数需要达到房间最小人数的一半！', e)

    # 检查如果是俄文楼，是否只有一个人使用
    if "R" in room.Rid:  # 如果是俄文楼系列
        try:
            assert len(
                students) + contents['non_yp_num'] == 1, f"too many people using russian room!"
        except Exception as e:
            return _error('俄文楼元创空间仅支持单人预约！', e)

    # 检查预约时间是否正确
    try:
        Astart = contents['Astart']
        Afinish = contents['Afinish']
        assert Astart <= Afinish, 'Appoint time error'

        # --- modify by lhw: Astart 可能比datetime.now小 --- #
        #assert Astart > datetime.now(), 'Appoint time error'
        assert Afinish > datetime.now(), 'Appoint time error'
        # --- modify end: 2021.7.10 --- #
    except Exception as e:
        return _error('非法预约时间段，请不要擅自修改url！', e)

    # 预约是否超过3小时
    try:
        assert Afinish <= Astart + timedelta(hours=3)
    except:
        return _error('预约时长不能超过3小时！')

    # 学号对了，人对了，房间是真实存在的，那就开始预约了
    # 接下来开始搜索数据库，上锁
    major_student = None    # 避免下面未声明出错
    try:
        with transaction.atomic():

            # 获取预约发起者,确认预约状态
            major_student = get_participant(contents['Sid'])
            if major_student is None:
                return _error('发起人信息不存在！')

            # 等待确认的和结束的肯定是当下时刻已经弄完的，所以不用管
            appoints = room.appoint_list.select_for_update().exclude(
                Astatus=Appoint.Status.CANCELED).filter(
                    Room_id=contents['Rid'])
            for appoint in appoints:
                start = appoint.Astart
                finish = appoint.Afinish

                # 第一种可能，开始在开始之前，只要结束的比开始晚就不行
                # 第二种可能，开始在开始之后，只要在结束之前就都不行
                if (start <= Astart < finish) or (Astart <= start < Afinish):
                    # 有预约冲突的嫌疑，但要检查一下是不是重复预约了
                    if (start == Astart and finish == Afinish
                            and appoint.Ausage == contents['Ausage']
                            and appoint.Aannouncement == contents['announcement']
                            and appoint.Ayp_num == len(students)
                            and appoint.Anon_yp_num == contents['non_yp_num']
                            and major_student == appoint.major_student):
                        # Room不用检查，肯定是同一个房间
                        # TODO: major_sid
                        utils.operation_writer(
                            major_student.Sid_id, "重复发起同时段预约，预约号"+str(appoint.Aid), "scheduler_func.addAppoint", "OK")
                        return _success(appoint.toJson())
                    else:
                        # 预约冲突
                        return _error('预约时间与已有预约冲突,请重选时间段!', appoint.toJson())

            # 确认信用分符合要求
            if major_student.credit <= 0:
                return _error('信用分不足，本月无法发起预约！')

            # 合法，可以返回了
            appoint = Appoint(Room=room,
                              Astart=Astart,
                              Afinish=Afinish,
                              Ausage=contents['Ausage'],
                              Aannouncement=contents['announcement'],
                              major_student=major_student,
                              Anon_yp_num=contents['non_yp_num'],
                              Ayp_num=len(students),
                              Aneed_num=real_min,
                              Atype=type,
                              Atemp_flag=contents['Atemp_flag'])
            appoint.save()
            appoint.students.set(students)

            # modify by pht: 整合定时任务为函数
            set_scheduler(appoint)
            set_start_wechat(appoint, students_id, notify_create=notify_create)

            utils.operation_writer(major_student.get_id(), "发起预约，预约号" +
                             str(appoint.Aid), "scheduler_func.addAppoint", "OK")

    except Exception as e:
        utils.operation_writer(SYSTEM_LOG, "学生" + str(major_student) +
                         "出现添加预约失败的问题:"+str(e), "scheduler_func.addAppoint", "Error")
        return _error('添加预约失败!请与管理员联系!')

    return _success(appoint.toJson())


def get_longterm_display(times: int, interval_week: int):
    if interval_week == 1:
        longterm_info = f'{times}周的'
    elif interval_week == 2:
        longterm_info = f'{times}次单/双周的'
    else:
        longterm_info = f'{times}次间隔{interval_week}周的'
    return longterm_info


def add_longterm_appoint(appoint: Appoint,
                         times: int,
                         interval: int = 1,
                         week_offset: int = 0,
                         admin: bool = False):
    '''
    自动开启事务以检查预约是否冲突，以原预约为模板直接生成新预约
        暂不检查预约时间是否合法
        **本函数中time的语义均为次数，不是时间
    
    返回值
        error_time: 发生错误的预约次数，成功为None，错误可能源于冲突或者
        appoints: 失败时返回冲突的预约，成功时返回生成的预约，开始时间顺序排列
    '''
    with transaction.atomic():
        conflict_appoints = utils.get_conflict_appoints(
            appoint, times, interval, week_offset, lock=True)
        if conflict_appoints:
            first_conflict = conflict_appoints[0]
            first_time = (
                (first_conflict.Afinish - appoint.Astart)
                // timedelta(weeks=interval) + 1)
            return first_time, conflict_appoints

        # 没有冲突，开始创建长线预约
        students = appoint.students.all()
        new_appoints = []
        new_appoint: Appoint = Appoint.objects.get(pk=appoint.pk)
        # 调整偏移
        new_appoint.Astart += timedelta(weeks=week_offset-interval)
        new_appoint.Afinish += timedelta(weeks=week_offset-interval)
        for time in range(times):
            # 先获取复制对象的副本
            new_appoint.Astart += timedelta(weeks=interval)
            new_appoint.Afinish += timedelta(weeks=interval)
            new_appoint.Astatus = Appoint.Status.APPOINTED
            new_appoint.Atype = Appoint.Type.LONGTERM
            # 删除主键会被视为新对象，save时向数据库添加对象并更新主键
            new_appoint.pk = None
            new_appoint.save()
            new_appoint.students.set(students)
            new_appoints.append(new_appoint.pk)

        # 获取长线预约集合，由于生成是按顺序的，默认排序也是按主键递增，无需重排
        new_appoints = Appoint.objects.filter(pk__in=new_appoints)
        # 至此，预约都已成功创建，可以放心设置定时任务了，但设置定时任务出错也需要回滚
        for new_appoint in new_appoints:
            set_scheduler(new_appoint)
            set_start_wechat(new_appoint, notify_create=False)

    # 长线化预约发起成功，准备消息提示即可
    longterm_info = get_longterm_display(times, interval)
    utils.operation_writer(
        appoint.get_major_id(),
        f"发起{longterm_info}长线化预约, 原预约号为{appoint.Aid}",
        "scheduler_func.add_longterm_appoint", "OK")
    return None, new_appoints
