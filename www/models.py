#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Models for user, blog, comment.
'''

__author__ = 'Morpheus Guo'

import time, uuid

from orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(default=time.time)

class Blog(Model):
    __table__ = 'projects'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    project_status = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    created_at = FloatField(default=time.time)

class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    blog_id = StringField(ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    content = TextField()
    created_at = FloatField(default=time.time)

class Finance(Model):
    __table__ = 'finance'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    month = StringField(ddl='varchar(50)')
    year = StringField(ddl='varchar(50)')
    revenue = StringField(ddl='varchar(50)')
    invoiced_or_not = StringField(ddl='varchar(50)')
    content = TextField()
    created_at = FloatField(default=time.time)

class Resource(Model):
    __table__ = 'resources'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    name = StringField(ddl='varchar(50)')
    employee_id = StringField(ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    introduce = StringField(ddl='varchar(500)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(default=time.time)
