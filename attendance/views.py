from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from .models import Attendance, leaders, Group, Member, Session


def homepage(request):
    return render(request, "attendance/homepage.html")

@csrf_protect
def login_view(request):
    return render(request, "attendance/login.html")

@csrf_protect
def supervisor_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff:
            auth_login(request, user)
            return redirect('admin_home')
        messages.error(request, "Invalid credentials or not an admin.")
    return render(request, 'registration/login.html')

def supervisor_logout(request):
    return redirect('supervisor_login')

@login_required
def admin_page(request):
    context = {
        'groups': Group.objects.all(),
        'members': Member.objects.all(),
        'leaders': leaders.objects.all()
    }
    return render(request, 'attendance/admin_homepage.html', context)

@csrf_protect
def view_attendance(request):
    sessions = Session.objects.all()
    if request.method == 'POST':
        session = get_object_or_404(Session, id=request.POST.get('session'))
        attendance_data = Attendance.objects.filter(session=session).select_related('member').order_by('member__group')
        present_count = attendance_data.filter(status=True).count()
        absent_count = attendance_data.filter(status=False).count()

        group_attendance = {group: [] for group in Group.objects.all()}
        for member in Member.objects.all():
            status = attendance_data.filter(member=member).first()
            if member.group:
                group_attendance[member.group].append(status)

        return render(request, 'attendance/view_attendance.html', {
            'sessions': sessions,
            'attendance_data': group_attendance,
            'session': session,
            'present_count': present_count,
            'absent_count': absent_count,
        })
    return render(request, 'attendance/view_attendance.html', {'sessions': sessions})

@csrf_protect
def manage_group(request):
    group_id = request.GET.get("group_id")
    selected_group = get_object_or_404(Group, id=group_id) if group_id else None
    return render(request, "attendance/manage_groups.html", {
        "groups": Group.objects.all(),
        "members": Member.objects.filter(group=selected_group) if selected_group else [],
        "selected_group": selected_group,
        "all_members": Member.objects.all(),
    })

@csrf_protect
def add_member(request):
    if request.method == "POST":
        member = get_object_or_404(Member, id=request.POST.get("member_id"))
        group = get_object_or_404(Group, id=request.POST.get("group_id"))
        member.group = group
        member.save()
    return redirect(f"/supervisor/manage-group/?group_id={group.id}")

@csrf_protect
def remove_member(request):
    if request.method == "POST":
        member = get_object_or_404(Member, id=request.POST.get("member_id"))
        group_id = member.group.id if member.group else None
        member.group = None
        member.save()
    return redirect(f"/supervisor/manage-group/?group_id={group_id}" if group_id else "/supervisor/manage-group/")

@csrf_protect
def assign_leader(request):
    groups = Group.objects.all()
    members = Member.objects.all()
    context = {
        'groups': groups,
        'members': members,
    }
    if request.method == 'POST':
        try:
            leader_member = get_object_or_404(Member, name=request.POST.get('name'))
            group = get_object_or_404(Group, name=request.POST.get('group'))
            leaders.objects.filter(name=leader_member).delete()
            leader, _ = leaders.objects.get_or_create(name=leader_member, group=group)
            leader.username = request.POST.get('username')
            leader.save()
            group.leader = leader_member
            group.save()
            #move member to that group id not in the group
            member = Member.objects.filter(name=leader_member).first()
            member.group = group
            member.save()
            messages.success(request, "Leader assigned successfully!")
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return render(request, 'attendance/assign_leader.html', context)

@csrf_protect
def check_login(request):
    if request.method == "POST":  
        try:
            leader = get_object_or_404(leaders, username=request.POST.get("username"))
            request.session["leader"] = leader.username
            request.session["leader_name"] = str(leader.name)
            return redirect("home")
        except leaders.DoesNotExist:
            messages.error(request, "Invalid username")
    return redirect("login")

@csrf_protect
def home(request):
    leader = leaders.objects.filter(username=request.session.get('leader')).first()
    if not leader:
        return render(request, "attendance/home.html", {"error": "Leader not found!"})
    group = leader.group
    unsubmitted_attendance = Attendance.objects.filter(member__group=group, submitted=False, member=leader.name)
    context = {
        "group": group,
        "unsubmitted_attendance": unsubmitted_attendance,
        "unsubmitted_sessions": [a.session for a in unsubmitted_attendance],
        "leader_name": request.session.get('leader_name', '').split()[0],
    }
    return render(request, "attendance/home.html", context)

@csrf_protect
def attendance(request, session_id):
    leader = leaders.objects.get(username=request.session.get('leader'))
    group = leader.group
    members = Member.objects.filter(group=group)
    session = get_object_or_404(Session, id=session_id)
    attendance_records = {a.member.id: a.status for a in Attendance.objects.filter(session=session, member__group=group)}
    for member in members:
        member.attendance_status = attendance_records.get(member.id, "Not Marked")
    return render(request, 'attendance/mark_attendance.html', {"members": members, "session": session})

@csrf_protect
def submit_attendance(request, session_id):
    leader = leaders.objects.get(username=request.session.get('leader'))
    group = leader.group
    members = Member.objects.filter(group=group)
    session = get_object_or_404(Session, id=session_id)
    if request.method == "POST":
        selected_members = request.POST.getlist("attendance")
        for member in members:
            status = member.id in map(int, selected_members)
            Attendance.objects.filter(session=session, member=member).update(status=status, submitted=True)
        return redirect("home")
    return render(request, "attendance/mark_attendance.html", {"members": members, "session": session})

def all_attendance(request):
    sessions = Session.objects.all().order_by("date")
    groups = Group.objects.all()

    # Preparing attendance data in a simple format
    attendance_data = {}

    for group in groups:
        members = Member.objects.filter(group=group)
        attendance_data[group] = {}

        for member in members:
            attendance_data[group][member] = {}
            for session in sessions:
                attendance = Attendance.objects.filter(member=member, session=session).first()
                attendance_data[group][member][session] = "Present" if attendance and attendance.status else "Absent"
    context = {
        "sessions": sessions,
        "attendance_data": attendance_data,
    }
    return render(request, "attendance/all_attendance.html", context)