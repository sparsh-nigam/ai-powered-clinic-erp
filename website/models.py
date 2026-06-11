from django.db import models

# Create your models here.
class WebsiteSettings(models.Model):
    website_name=models.CharField(max_length=200)
    hero_heading=models.CharField(max_length=300)
    hero_message=models.TextField()
    
    def __str__(self):
        return self.website_name