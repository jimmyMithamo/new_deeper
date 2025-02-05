from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login
from .models import Attendance, leaders, Group, Member, Session
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect


def homepage(request):
    return render(request, "attendance/homepage.html")

@csrf_protect
def login_view(request):  # Rename to avoid conflict
    return render(request, "attendance/login.html")

@csrf_protect
def supervisor_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:  # check if user is admin
            login(request, user)
            return redirect('supervisor_dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials or not an admin.'})
    return render(request, 'attendance/admin_login.html')

@csrf_protect
def admin_page(request):
    # Fetch the data required for the homepage
    groups = Group.objects.all()
    members = Member.objects.all()
    leaders_list = leaders.objects.all()

    context = {
        'groups': groups,
        'members': members,
        'leaders': leaders_list,
    }
    
    return render(request, 'attendance/admin_homepage.html', context)

@csrf_protect
def view_attendance(request):
    # Get all sessions
    sessions = Session.objects.all()
    if request.method == 'POST':
        session_id = request.POST.get('session')
        session = Session.objects.get(id=session_id)
        
        # Get all members and their attendance status for this session
        attendance_data = Attendance.objects.filter(session=session).select_related('member').order_by('member__group')
        
        # Count the number of present and absent attendees
        present_count = attendance_data.filter(status='True').count()
        absent_count = attendance_data.filter(status='False').count()

        # Arrange attendees by group
        groups = Group.objects.all()
        group_attendance = {}
        for group in groups:
            group_members = group.member_set.all()
            group_attendance[group] = []
            for member in group_members:
                status = attendance_data.filter(member=member).first()
                group_attendance[group].append(status)

        return render(request, 'attendance/view_attendance.html', {
            'sessions': sessions,
            'attendance_data': group_attendance,
            'session': session,
            'present_count': present_count,
            'absent_count': absent_count,
        })

    return render(request, 'attendance/view_attendance.html', {
        'sessions': sessions,
    })
@csrf_protect
def manage_group(request):
    groups = Group.objects.all()
    members = []
    selected_group = None

    group_id = request.GET.get("group_id")
    if group_id:
        selected_group = get_object_or_404(Group, id=group_id)
        members = Member.objects.filter(group=selected_group)

    all_members = Member.objects.all()

    return render(request, "attendance/admin_dashboard.html", {
        "groups": groups,
        "members": members,
        "selected_group": selected_group,
        "all_members": all_members,
    })
@csrf_protect
def add_member(request):
    if request.method == "POST":
        member_id = request.POST.get("member_id")
        group_id = request.POST.get("group_id")

        member = get_object_or_404(Member, id=member_id)
        group = get_object_or_404(Group, id=group_id)

        member.group = group
        member.save()

    return redirect(f"/supervisor/manage-group/?group_id={group_id}")
@csrf_protect
def remove_member(request):
    if request.method == "POST":
        member_id = request.POST.get("member_id")

        member = get_object_or_404(Member, id=member_id)
        group_id = member.group.id if member.group else None  # Store group ID before removal

        member.group = None  # Remove the member from the group
        member.save()

        if group_id:
            return redirect(f"/supervisor/manage-group/?group_id={group_id}")
        else:
            return redirect("/supervisor/manage-group/")  # Redirect safely if no group
@csrf_protect
def assign_leader(request):
    if request.method == 'POST':
        # Retrieve the leader's name, username, and group ID from the POST data
        leader_name = request.POST.get('name')
        username = request.POST.get('username')
        group_name = request.POST.get('group')

        # Check if the required data is provided
        if leader_name and username and group_name:
            try:
                # Fetch the leader, group, and update accordingly
                leader_member = Member.objects.get(name=leader_name)
                group = Group.objects.get(name=group_name)

                # Check if the leader is already assigned to another group
                current_leader = leaders.objects.filter(name=leader_member).first()
                if current_leader:
                    # If the leader is assigned to another group, remove them
                    current_leader.group.leader = None  # Unassign leader from previous group
                    current_leader.group.save()
                    current_leader.delete()

                # Create or update the leader entry
                leader, created = leaders.objects.get_or_create(
                    name=leader_member,
                    group=group
                )
                leader.username = username
                leader.save()

                # Update the group with the new leader
                group.leader = leader_member
                group.save()

                # Pass a success message to the template
                return render(request, 'assign_leader.html', {
                    'message': "Leader assigned successfully!",
                    'groups': Group.objects.all(),
                    'members': Member.objects.all()
                })

            except Member.DoesNotExist:
                return HttpResponse("Leader not found.", status=400)
            except Group.DoesNotExist:
                return HttpResponse("Group not found.", status=400)
        else:
            return HttpResponse("Missing data.", status=400)

    # For GET requests, render the form to assign leaders
    groups = Group.objects.all()
    members = Member.objects.all()
    return render(request, 'attendance/assign_leader.html', {'groups': groups, 'members': members})






@csrf_protect
def check_login(request):
    if request.method == "POST":  
        username = request.POST.get("username")

        try:
            # Check if the user exists in the 'Member' table and is a leader
            leader = leaders.objects.get(username=username)

            # Store leader's ID in session for authentication
            request.session["leader"] = leader.username
            request.session["leader_name"] = str(leader.name)

            return redirect("home")  # Ensure 'home' exists in your URLs

        except leaders.DoesNotExist:
            return render(request, "attendance/login.html", {"error": "Invalid username"})

    return redirect("login")  # Redirect to login page if method is not POST
@csrf_protect
def home(request):
    leader_username = request.session.get('leader')  # Get leader from session
    print('Leader username:', leader_username)

    try:
        leader = leaders.objects.get(username=leader_username)  # Get leader object
        group = leader.group
        print('Group:', group)

        # Query for unsubmitted attendance related to the leader's group
        unsubmitted_attendance = Attendance.objects.filter(member__group=group, submitted=False, member = leader.name)
        unsubmitted_sessions = [a.session for a in unsubmitted_attendance]
        

        context = {
            "group": group,
            "unsubmitted_attendance": unsubmitted_attendance,
            "unsubmitted_sessions": unsubmitted_sessions,
            "leader_name": str(request.session.get('leader_name')).split()[0],  # Get first name
        }

        return render(request, "attendance/home.html", context=context)

    except leaders.DoesNotExist:
        print("Leader not found!")
        return render(request, "attendance/home.html", {"error": "Leader not found!"})
@csrf_protect
def attendance(request, session_id):
    leader = request.session.get('leader')

    # Get the leader's group
    group = leaders.objects.get(username=leader).group
    leader_name = leaders.objects.get(username=leader).name
    print('Leader:', leader_name)

    # Fetch members belonging to the group
    members = Member.objects.filter(group=group)

    # Fetch the latest session
    #look for attendance seesion of leader not submitted
    unsubmitted_attendance = Attendance.objects.filter(member__group=group, submitted=False, member = leader_name)
    session = get_object_or_404(Session, id=session_id)

    #session = Session.objects.get(id=session_id)

    # Fetch attendance as a dictionary {member_id: attendance_object}
    attendance_records = {a.member.id: a.status for a in Attendance.objects.filter(session=session, member__group=group)}

    # Attach attendance status to members
    for member in members:
        member.attendance_status = attendance_records.get(member.id, "Not Marked")  # Default if not found

    context = {
        "members": members,
        "session": session,
    }

    return render(request, 'attendance/mark_attendance.html', context)
@csrf_protect
def submit_attendance(request, session_id):
    leader = request.session.get('leader')

    # Get the leader's group
    group = leaders.objects.get(username=leader).group

    # Fetch members belonging to the group
    members = Member.objects.filter(group=group)

    # Fetch the latest session
    session = get_object_or_404(Session, id=session_id)

    if request.method == "POST":
        selected_members = request.POST.getlist("attendance")  # List of member IDs marked as present

        for member in members:
            # Fetch all attendance records for this session and member
            attendance_records = Attendance.objects.filter(session=session, member=member)

            # Update all attendance records based on whether the member is marked as present
            if str(member.id) in selected_members:
                # Mark as present (True)
                attendance_records.update(status=True, submitted=True)
            else:
                # Mark as absent (False)
                attendance_records.update(status=False, submitted=True)

        return redirect("home")  # Reload page after submission

    # Attach attendance status to members
    attendance_records = {a.member.id: a for a in Attendance.objects.filter(session=session, member__group=group)}

    for member in members:
        # Default False if no attendance record exists
        member.attendance_status = attendance_records.get(member.id, False)

    context = {
        "members": members,
        "session": session,
    }
    return render(request, "attendance/mark_attendance.html", context)