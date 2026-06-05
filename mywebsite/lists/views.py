from django.shortcuts import render, redirect
from lists.models import Item, List

# 1. 首页主厨：只负责渲染空表单
def home_page(request):
    return render(request, 'home.html')

# 2. 专属展示页主厨：负责查出当前清单，并把它传给前端
def view_list(request, list_id):
    list_user = List.objects.get(id=list_id)
    # 【核心修复】：字典里的键必须是 'list'，和前端模板保持绝对一致！
    return render(request, 'list.html', {'list': list_user})

# 3. 新建清单主厨：创建新 List 和第一条 Item
def new_list(request):
    list_user = List.objects.create()
    Item.objects.create(text=request.POST['item_text'], list=list_user)
    return redirect(f'/lists/{list_user.id}/')

# 4. 追加事项主厨：找到已有 List，直接追加 Item
def add_item(request, list_id):
    list_user = List.objects.get(id=list_id)
    Item.objects.create(text=request.POST['item_text'], list=list_user)
    return redirect(f'/lists/{list_user.id}/')