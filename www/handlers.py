#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Morpheus Guo'

' url handlers '

import re, time, json, logging, hashlib, base64, asyncio

import markdown2

from aiohttp import web

from coroweb import get, post
from apis import Page, APIValueError, APIResourceNotFoundError

from models import User, Comment, Blog, next_id, Resource, Finance
from config import configs

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

def user2cookie(user, max_age):
    '''
    Generate cookie str by user.
    '''
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)

@asyncio.coroutine
def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid.
    '''
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = yield from User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None

@get('/')
def index(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Blog.findNumber('count(id)')
    page = Page(num)
    if num == 0:
        blogs = []
    else:
        blogs = yield from Blog.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))
    return {
        '__template__': 'blogs.html',
        'page': page,
        'blogs': blogs
    }

@get('/chart')
def chart(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Finance.findNumber('count(id)')
    page = Page(num)
    if num == 0:
        finances = []
    else:
        finances = yield from Finance.findAll(orderBy='created_at desc')
    rev = []
    for fin in finances:
        rev.append(int(fin.revenue))
    return {
        '__template__': 'chart.html',
        'page': page,
        'finances': finances,
        'rev': rev
    }

@get('/team')
def team(*, page='1'):
    return {
        '__template__': 'team.html',
        'page_index': get_page_index(page)
    }

@get('/manage/finance')
def finance(*, page='1'):
    return {
        '__template__': 'finance_management.html',
        'page_index': get_page_index(page)
    }

@get('/dashboard')
def dashboard(*, page='1'):
    num = yield from Finance.findNumber('count(id)')
    page = Page(num)
    if num == 0:
        finances = []
    else:
        finances = yield from Finance.findAll(orderBy='created_at desc')
    rev = []
    for fin in finances:
        rev.append(int(fin.revenue))
    return {
        '__template__': 'dashboard.html',
        'page': page,
        'finances': finances,
        'rev': rev
    }

@get('/about')
def about(*, page='1'):
    return {
        '__template__': 'about.html'
    }

@get('/blog/{id}')
def get_blog(id):
    blog = yield from Blog.find(id)
    comments = yield from Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
    for c in comments:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    num = yield from Finance.findNumber('count(id)')
    page = Page(num)
    if num == 0:
        finances = []
    else:
        finances = yield from Finance.findAll(orderBy='created_at desc')
    rev = []
    for fin in finances:
        rev.append(int(fin.revenue))
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments,
        'page': page,
        'finances': finances,
        'rev': rev
    }

@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }

@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }

@post('/api/authenticate')
def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid password.')
    users = yield from User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]
    # check passwd:
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid password.')
    # authenticate ok, set cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound('/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out.')
    return r

@get('/manage/')
def manage():
    return 'redirect:/manage/comments'

@get('/manage/comments')
def manage_comments(*, page='1'):
    return {
        '__template__': 'manage_comments.html',
        'page_index': get_page_index(page)
    }

@get('/manage/blogs')
def manage_blogs(*, page='1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page)
    }

@get('/manage/blogs/create')
def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs'
    }

@get('/resources/edit')
def manage_edit_resource(*, id):
    return {
        '__template__': 'create_employee.html',
        'id': id,
        'action': '/api/resources/%s' % id
    }

@get('/create_finance')
def manage_create_finance():
    return {
        '__template__': 'create_finance.html',
        'id': '',
        'action': '/api/finances'
    }


@get('/finances/edit')
def manage_edit_finance(*, id):
    return {
        '__template__': 'create_finance.html',
        'id': id,
        'action': '/api/finances/%s' % id
    }

@get('/create_employee')
def manage_create_employee():
    return {
        '__template__': 'create_employee.html',
        'id': '',
        'action': '/api/resources'
    }

@get('/manage/blogs/edit')
def manage_edit_blog(*, id):
    return {
        '__template__': 'manage_blog_edit.html',
        'id': id,
        'action': '/api/blogs/%s' % id
    }

@get('/manage/users')
def manage_users(*, page='1'):
    return {
        '__template__': 'manage_users.html',
        'page_index': get_page_index(page)
    }

@get('/api/comments')
def api_comments(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Comment.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, comments=())
    comments = yield from Comment.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, comments=comments)

@post('/api/blogs/{id}/comments')
def api_create_comment(id, request, *, content):
    user = request.__user__
    if user is None:
        raise APIPermissionError('Please signin first.')
    if not content or not content.strip():
        raise APIValueError('content')
    blog = yield from Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    comment = Comment(blog_id=blog.id, user_id=user.id, user_name=user.name, user_image=user.image, content=content.strip())
    yield from comment.save()
    return comment

@post('/api/comments/{id}/delete')
def api_delete_comments(id, request):
    check_admin(request)
    c = yield from Comment.find(id)
    if c is None:
        raise APIResourceNotFoundError('Comment')
    yield from c.remove()
    return dict(id=id)

@get('/api/users')
def api_get_users(*, page='1'):
    page_index = get_page_index(page)
    num = yield from User.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, users=())
    users = yield from User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    for u in users:
        u.passwd = '******'
    return dict(page=p, users=users)

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

@post('/api/users')
def api_register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = yield from User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    yield from user.save()
    # make session cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

@get('/api/blogs')
def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Blog.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = yield from Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)

@get('/api/resources')
def api_resources(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Resource.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, resources=())
    resources = yield from Resource.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, resources=resources)

@get('/api/finances')
def api_finance(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Finance.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, finances=())
    finances = yield from Finance.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, finances=finances)

@get('/api/blogs/{id}')
def api_get_blog(*, id):
    blog = yield from Blog.find(id)
    return blog

@post('/api/blogs')
def api_create_blog(request, *, name, summary, content, project_status):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    if not project_status or not project_status.strip():
        raise APIValueError('project_status', 'project_status cannot be empty.')
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip(), project_status=project_status.strip())
    yield from blog.save()
    return blog

@get('/api/resources/{id}')
def api_get_resource(*, id):
    resource = yield from Resource.find(id)
    return

@get('/api/finances/{id}')
def api_get_resource(*, id):
    finance = yield from Finance.find(id)
    return finance

@post('/api/resources')
def api_create_resource(request, *, name, employee_id, email, introduce):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not employee_id or not employee_id.strip():
        raise APIValueError('employee_id', 'employee_id cannot be empty.')
    if not email or not email.strip():
        raise APIValueError('email', 'email cannot be empty.')
    if not introduce or not introduce.strip():
        raise APIValueError('introduce', 'introduce cannot be empty.')
    resource = Resource(name=name.strip(), employee_id=employee_id.strip(), image=request.__user__.image, email=email.strip(), introduce=introduce.strip())
    yield from resource.save()
    return resource

@post('/api/finances')
def api_create_finance(request, *, month, year, revenue, invoiced_or_not, content):
    check_admin(request)
    if not month or not month.strip():
        raise APIValueError('month', 'month cannot be empty.')
    if not year or not year.strip():
        raise APIValueError('year', 'year cannot be empty.')
    if not revenue or not revenue.strip():
        raise APIValueError('revenue', 'revenue cannot be empty.')
    if not invoiced_or_not or not invoiced_or_not.strip():
        raise APIValueError('introduce', 'introduce cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    finance = Finance(month=month.strip(), year=year.strip(), revenue=revenue.strip(),invoiced_or_not=invoiced_or_not.strip(), content=content.strip())
    yield from finance.save()
    return finance

@post('/api/blogs/{id}')
def api_update_blog(id, request, *, name, summary, content, project_status):
    check_admin(request)
    blog = yield from Blog.find(id)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    if not project_status or not project_status.strip():
        raise APIValueError('project_status', 'project_status cannot be empty.')
    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    blog.project_status = project_status.strip()
    yield from blog.update()
    return blog

@post('/api/resources/{id}')
def api_update_resource(id, request, *, name, employee_id, email, introduce):
    check_admin(request)
    resource = yield from Resource.find(id)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not employee_id or not employee_id.strip():
        raise APIValueError('employee_id', 'employee_id cannot be empty.')
    if not email or not email.strip():
        raise APIValueError('email', 'email cannot be empty.')
    if not introduce or not introduce.strip():
        raise APIValueError('introduce', 'introduce cannot be empty.')
    resource.name = name.strip()
    resource.employee_id = employee_id.strip()
    resource.email = email.strip()
    resource.introduce = introduce.strip()
    yield from resource.update()
    return resource

@post('/api/finances/{id}')
def api_update_finance(id, request, *, month, year, revenue, invoiced_or_not, content):
    check_admin(request)
    finance = yield from Finance.find(id)
    if not month or not month.strip():
        raise APIValueError('month', 'month cannot be empty.')
    if not year or not year.strip():
        raise APIValueError('year', 'year cannot be empty.')
    if not revenue or not revenue.strip():
        raise APIValueError('revenue', 'revenue cannot be empty.')
    if not invoiced_or_not or not invoiced_or_not.strip():
        raise APIValueError('introduce', 'introduce cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    finance.month = month.strip()
    finance.year = year.strip()
    finance.revenue = revenue.strip()
    finance.invoiced_or_not = invoiced_or_not.strip()
    finance.content = content.strip()
    yield from finance.update()
    return finance

@post('/api/blogs/{id}/delete')
def api_delete_blog(request, *, id):
    check_admin(request)
    blog = yield from Blog.find(id)
    yield from blog.remove()
    return dict(id=id)


@post('/api/resources/{id}/delete')
def api_delete_resource(request, *, id):
    check_admin(request)
    resource = yield from Resource.find(id)
    yield from resource.remove()
    return dict(id=id)

@post('/api/finances/{id}/delete')
def api_delete_finance(request, *, id):
    check_admin(request)
    finance = yield from Finance.find(id)
    yield from finance.remove()
    return dict(id=id)