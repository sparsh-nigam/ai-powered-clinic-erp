from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    Role_Choices = (
        ('SUPER_OWNER','Super Owner'),
        ('STAFF','Staff'),
        ('DOCTOR','Doctor'),
    )
    
    role = models.CharField(
        max_length=20,
        choices=Role_Choices
    )
