from django.db import models

class List(models.Model): # 修改了这里
    pass

class Item(models.Model):
    text = models.TextField(default='')
    # 新增下面这行：用外键关联 List，级联删除，给个默认值
    list = models.ForeignKey(List, on_delete=models.CASCADE, default=None)