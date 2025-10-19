from django.db import models
from datetime import date

class Cluster(models.Model):
    clusterid = models.IntegerField(primary_key=True)
    clustername = models.CharField(max_length=100)

    class Meta:
        db_table = 'cluster'

    def __str__(self):
        return self.clustername


class AppUser(models.Model):
    username = models.CharField(max_length=20, primary_key=True)
    passwrd = models.CharField(max_length=25)
    usertype = models.IntegerField()

    class Meta:
        db_table = 'appuser'

    def __str__(self):
        return self.username


class AgeGroup(models.Model):
    agegroupid = models.IntegerField(primary_key=True)
    agegroup = models.CharField(max_length=15)

    class Meta:
        db_table = 'agegroup'
        managed = False

    def __str__(self):
        return self.agegroup


class State(models.Model):
    stateid = models.IntegerField(primary_key=True)
    statename = models.CharField(max_length=30)

    class Meta:
        db_table = 'state'

    def __str__(self):
        return self.statename


class Post(models.Model):
    postid = models.IntegerField(primary_key=True)
    clusterid = models.ForeignKey(Cluster, on_delete=models.CASCADE, db_column='clusterid')
    postdate = models.DateField()
    postlink = models.CharField(max_length=2048)
    postmessage = models.CharField(max_length=2048)

    class Meta:
        db_table = 'post'

    def __str__(self):
        return f"Post {self.postid} - {self.postmessage[:50]}"


class Response(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Others'),
        ('N', 'Not Disclosed'),
    ]

    SENTIMENT_CHOICES = [
        ('P', 'Positive'),
        ('N', 'Negative'),
        ('U', 'Neutral'),
    ]

    # Note: For responses where users don't disclose their information:
    # - agegroupid should be 0 (NA)
    # - gender should be 'N' (Not Disclosed)
    # - stateid should be 0 (NA)

    responseid = models.IntegerField(primary_key=True)
    postid = models.ForeignKey(Post, on_delete=models.CASCADE, db_column='postid')
    responsedate = models.DateField()
    responsemessage = models.CharField(max_length=1024)
    username = models.CharField(max_length=50)
    agegroupid = models.ForeignKey(AgeGroup, on_delete=models.CASCADE, db_column='agegroupid')
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES, default='NA')
    stateid = models.ForeignKey(State, on_delete=models.CASCADE, db_column='stateid')
    sentiment = models.CharField(max_length=1, choices=SENTIMENT_CHOICES)

    class Meta:
        db_table = 'response'

    def __str__(self):
        return f"Response {self.responseid} - {self.sentiment}"