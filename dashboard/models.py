from django.db import models
from django.contrib.auth.models import User

class AppUser(models.Model):
    USERTYPE_CHOICES = [
        (1, 'Admin'),
        (2, 'Public'),
    ]
    username = models.CharField(max_length=20, primary_key=True)
    passwrd = models.CharField(max_length=25)
    usertype = models.IntegerField(choices=USERTYPE_CHOICES)

    class Meta:
        db_table = 'appuser'

    def __str__(self):
        return self.username


class Cluster(models.Model):
    clusterid = models.AutoField(primary_key=True)
    clustername = models.CharField(max_length=100)

    class Meta:
        db_table = 'cluster'

    def __str__(self):
        return self.clustername


class Post(models.Model):
    postid = models.AutoField(primary_key=True)
    clusterid = models.ForeignKey(Cluster, on_delete=models.CASCADE, db_column='clusterid')
    postlink = models.URLField(max_length=2048)
    postmessage = models.TextField(max_length=2048)

    class Meta:
        db_table = 'post'

    def __str__(self):
        return f"Post {self.postid}"


class AgeGroup(models.Model):
    agegroupid = models.AutoField(primary_key=True)
    agegroup = models.CharField(max_length=15)

    class Meta:
        db_table = 'agegroup'

    def __str__(self):
        return self.agegroup


class Response(models.Model):
    SENTIMENT_CHOICES = [
        ('P', 'Positive'),
        ('N', 'Negative'),
        ('U', 'Neutral'),
    ]
    responseid = models.AutoField(primary_key=True)
    postid = models.ForeignKey(Post, on_delete=models.CASCADE, db_column='postid')
    responsemessage = models.CharField(max_length=1024)
    username = models.CharField(max_length=50)
    agegroupid = models.ForeignKey(AgeGroup, on_delete=models.SET_NULL, null=True, db_column='agegroupid')
    gender = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')])
    location = models.CharField(max_length=30)
    sentiment = models.CharField(max_length=1, choices=SENTIMENT_CHOICES)

    class Meta:
        db_table = 'response'

    def __str__(self):
        return f"Response {self.responseid}"