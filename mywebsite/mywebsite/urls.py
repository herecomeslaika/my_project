from django.urls import path, include
from lists import views as list_views  # 给 views 起个别名，避免混淆
from lists import urls as list_urls    # 导入刚刚写好的子路由模块

urlpatterns = [
    # 首页依然由主控台直接负责
    path('', list_views.home_page, name='home'),
    
    # 核心重构：将所有以 lists/ 开头的请求，无脑转交给 list_urls 处理！
    path('lists/', include(list_urls)),
]