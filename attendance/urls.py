from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [
    path("login/", views.login_view, name="login"),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path("check_login/", views.check_login, name="check_login"),
    path("home/", views.home, name="home"),
    path("mark_attendance/<int:session_id>/", views.attendance, name="mark_attendance"),
    path("submit_attendance/<int:session_id>/", views.submit_attendance, name="submit_attendance"),
    path('supervisor/', views.admin_page, name='admin_home'),
    path('supervisor/login/', views.supervisor_login, name='supervisor_login'),
    path("supervisor/manage-group/", views.manage_group, name="manage_group"),
    path("supervisor/add-member/", views.add_member, name="add_member"),
    path("supervisor/remove-member/", views.remove_member, name="remove_member"),
    path('supervisor/assign-leader/', views.assign_leader, name='assign_leader'),
    path('' , views.homepage, name='homepage'),
    path('supervisor/view_attendance/', views.view_attendance, name='view_attendance'),



]
