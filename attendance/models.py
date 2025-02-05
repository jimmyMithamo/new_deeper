from django.db import models
from django.utils import timezone

# model for members
class Member(models.Model):
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    group = models.ForeignKey("Group", on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name
    
class leaders(models.Model):
    name = models.ForeignKey(Member, on_delete=models.CASCADE)
    username = models.CharField(max_length=100, null=True, blank=True)
    group = models.ForeignKey("Group", on_delete=models.CASCADE)

    

# model for groups
class Group(models.Model):
    name = models.CharField(max_length=100)
    leader = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="led_groups",  # Custom related name
    )

    def __str__(self):
        return self.name
    
# model for sessions_calendar
class Session(models.Model):
    name = models.CharField(max_length=100)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically set on creation


    def __str__(self):
        return str(self.date)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Save the session first
        members = Member.objects.all()
        for member in members:
            Attendance.objects.get_or_create(member=member, session=self)
    
# model for attendance
class Attendance(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    status = models.BooleanField(null=True, default = False)
    submitted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.member} - {self.session}"
    