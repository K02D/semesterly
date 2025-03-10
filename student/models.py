# Copyright (C) 2017 Semester.ly Technologies, LLC
#
# Semester.ly is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Semester.ly is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

""" Models pertaining to Students. """

from django.core.signing import TimestampSigner
from django.db import models
from django.contrib.auth.models import User
from django.forms import model_to_dict
from hashids import Hashids
from oauth2client.client import GoogleCredentials
import timetable.models as timetable_models
from semesterly.settings import get_secret

hashids = Hashids(salt=get_secret("HASHING_SALT"))


class Student(models.Model):
    """Database object representing a student.

    A student is the core user of the app. Thus, a student will have a
    class year, major, friends, etc. An object is only created for the
    user if they have signed up (that is, signed out users are not
    represented by Student objects).
    """

    FRESHMAN = "FR"
    SOPHOMORE = "SO"
    JUNIOR = "JR"
    SENIOR = "SR"

    preferred_name = models.CharField(max_length=150, blank=True, null=True)
    class_year = models.IntegerField(blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.deletion.CASCADE)
    img_url = models.CharField(max_length=300, default=-1)
    friends = models.ManyToManyField("self", blank=True)
    fbook_uid = models.CharField(max_length=255, default="")
    major = models.CharField(max_length=255, default="")
    social_courses = models.BooleanField(null=True)
    social_offerings = models.BooleanField(null=True)
    social_all = models.BooleanField(null=True)
    emails_enabled = models.BooleanField(null=True, default=True)
    integrations = models.ManyToManyField(timetable_models.Integration, blank=True)
    time_created = models.DateTimeField(auto_now_add=True)
    school = models.CharField(max_length=100, null=True)
    time_accepted_tos = models.DateTimeField(null=True)
    jhed = models.CharField(max_length=255, null=True, default="")

    def __str__(self):
        return "{0}".format(self.jhed)

    def __unicode__(self):
        return "%s" % (self.jhed)

    def get_token(self):
        return TimestampSigner().sign(self.id).split(":", 1)[1]

    def get_hash(self):
        return hashids.encrypt(self.id)

    def is_signed_up_through_fb(self):
        return self.provider_exists("facebook")

    def is_signed_up_through_google(self):
        return self.provider_exists("google-oauth2")

    def is_signed_up_through_jhu(self):
        return self.provider_exists("azuread-tenant-oauth2")

    def provider_exists(self, provider):
        return self.user.social_auth.filter(provider=provider).exists()

    def is_logged_in_google(self):
        credentials = self.get_google_credentials()
        return credentials is not None and (not credentials.invalid)

    def get_google_credentials(self):
        social_user = self.user.social_auth.filter(provider="google-oauth2").first()
        if social_user is None:
            return None
        access_token = social_user.extra_data["access_token"]
        refresh_token = social_user.extra_data.get("refresh_token")
        expires_at = social_user.extra_data["expires"]
        return GoogleCredentials(
            access_token,
            get_secret("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY"),
            get_secret("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET"),
            refresh_token,
            expires_at,
            "https://accounts.google.com/o/oauth2/token",
            "my-user-agent/1.0",
        )


class Reaction(models.Model):
    """Database object representing a reaction to a course.

    A Reaction is performed by a Student on a Course, and can be one of REACTION_CHOICES
    below. The reaction itself is represented by its `title` field.
    """

    REACTION_CHOICES = (
        ("FIRE", "FIRE"),
        ("LOVE", "LOVE"),
        ("CRAP", "CRAP"),
        ("OKAY", "OKAY"),
        ("BORING", "BORING"),
        ("HARD", "HARD"),
        ("EASY", "EASY"),
        ("INTERESTING", "INTERESTING"),
    )
    student = models.ForeignKey("student.Student", on_delete=models.deletion.CASCADE)
    course = models.ManyToManyField(timetable_models.Course)
    title = models.CharField(max_length=50, choices=REACTION_CHOICES)
    time_created = models.DateTimeField(auto_now_add=True)


class PersonalEvent(models.Model):
    """
    A custom event that has been saved to a user's PersonalTimetable so that it persists
    across refresh, device, and session. Marks when a user is not free. Courses are
    scheduled around it.
    """

    timetable = models.ForeignKey(
        "PersonalTimetable",
        related_name="events",
        on_delete=models.deletion.CASCADE,
        null=True,
    )
    name = models.CharField(max_length=50)
    day = models.CharField(max_length=1)
    time_start = models.CharField(max_length=15)
    time_end = models.CharField(max_length=15)
    color = models.CharField(max_length=7, default="#F8F6F7")
    location = models.CharField(max_length=50, null=True, blank=True)
    credits = models.DecimalField(
        max_digits=3, decimal_places=1, default=0.0, null=True, blank=True
    )

    def __repr__(self):
        return repr(model_to_dict(self))


class PersonalTimetable(timetable_models.Timetable):
    """Database object representing a timetable created (and saved) by a user.

    A PersonalTimetable belongs to a Student, and contains a list of Courses and
    Sections that it represents.
    """

    name = models.CharField(max_length=100)
    student = models.ForeignKey(Student, on_delete=models.deletion.CASCADE)
    last_updated = models.DateTimeField(auto_now=True)
    has_conflict = models.BooleanField(blank=True, default=False)
    show_weekend = models.BooleanField(blank=True, default=True)


class RegistrationToken(models.Model):
    """A push notification token for Chrome notification via Google Cloud Messaging"""

    auth = models.TextField(default="")
    p256dh = models.TextField(default="")
    endpoint = models.TextField(default="")
    student = models.ForeignKey(
        Student, null=True, default=None, on_delete=models.deletion.CASCADE
    )
