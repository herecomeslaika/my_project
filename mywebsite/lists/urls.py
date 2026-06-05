from django.urls import path, re_path
from lists import views

urlpatterns = [
    # 注意：前面的 'lists/' 前缀都被去掉了，因为父级路由会处理它
    path('new', views.new_list, name='new_list'),
    re_path(r'^(\d+)/$', views.view_list, name='view_list'),
    re_path(r'^(\d+)/add_item$', views.add_item, name='add_item'),
]