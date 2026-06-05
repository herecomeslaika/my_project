from django.test import TestCase
from lists.models import Item, List  # 确保导入了 Item 和 List 模型

class HomePageTest(TestCase):

    def test_uses_home_template(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'home.html')



    def test_saving_and_retrieving_items(self):
        # 1. 先创建一个父清单，并保存到数据库
        list_user = List()
        list_user.save()

        # 2. 创建第一个 Item，并把它挂到这个清单上
        first_item = Item()
        first_item.text = 'The first (ever) list item'
        first_item.list = list_user  # 关键修复：指定所属清单
        first_item.save()

        # 3. 创建第二个 Item，同样挂上去
        second_item = Item()
        second_item.text = 'Item the second'
        second_item.list = list_user # 关键修复：指定所属清单
        second_item.save()

        # 4. 验证清单是否正确保存
        saved_list = List.objects.first()
        self.assertEqual(saved_list, list_user)

        # 5. 验证待办事项是否正确保存，并且属于刚才的清单
        saved_items = Item.objects.all()
        self.assertEqual(saved_items.count(), 2)

        first_saved_item = saved_items[0]
        second_saved_item = saved_items[1]
        self.assertEqual(first_saved_item.text, 'The first (ever) list item')
        self.assertEqual(first_saved_item.list, list_user) # 验证归属
        self.assertEqual(second_saved_item.text, 'Item the second')
        self.assertEqual(second_saved_item.list, list_user) # 验证归属
class ListViewTest(TestCase):

    def test_uses_list_template(self):
        list_user = List.objects.create()
        # 把假网址替换成真正的动态 URL（利用 f-string 填入 ID）
        response = self.client.get(f'/lists/{list_user.id}/')
        self.assertTemplateUsed(response, 'list.html')

    # 【全新替换】测试是否做到了数据隔离
    def test_displays_only_items_for_that_list(self):
        correct_list = List.objects.create()
        Item.objects.create(text='itemey 1', list=correct_list)
        Item.objects.create(text='itemey 2', list=correct_list)

        other_list = List.objects.create()
        Item.objects.create(text='other list item 1', list=other_list)
        Item.objects.create(text='other list item 2', list=other_list)

        # 访问属于 correct_list 的专属页面
        response = self.client.get(f'/lists/{correct_list.id}/')

        # 网页里应该有自己的待办事项
        self.assertContains(response, 'itemey 1')
        self.assertContains(response, 'itemey 2')
        # 网页里绝对不能有别人的待办事项！
        self.assertNotContains(response, 'other list item 1')
        self.assertNotContains(response, 'other list item 2')
    def test_passes_correct_list_to_template(self):
        other_list = List.objects.create()
        correct_list = List.objects.create()
        response = self.client.get(f'/lists/{correct_list.id}/')
        # 断言传递给模板的 'list' 变量正是我们请求的那个
        self.assertEqual(response.context['list'], correct_list)
class NewListTest(TestCase):

    def test_can_save_a_POST_request(self):
        # 注意：这里的目标 URL 变成了 /lists/new
        self.client.post('/lists/new', data={'item_text': 'A new list item'})
        self.assertEqual(Item.objects.count(), 1)
        new_item = Item.objects.first()
        self.assertEqual(new_item.text, 'A new list item')

    def test_redirects_after_POST(self):
        response = self.client.post('/lists/new', data={'item_text': 'A new list item'})
        new_list = List.objects.first()
        # 【修改断言】：期望跳转到真正的动态 ID 网址
        self.assertRedirects(response, f'/lists/{new_list.id}/')
class NewItemTest(TestCase):

    def test_can_save_a_POST_request_to_an_existing_list(self):
        other_list = List.objects.create()
        correct_list = List.objects.create()

        # 向正确的清单通道发送 POST 请求追加事项
        self.client.post(
            f'/lists/{correct_list.id}/add_item',
            data={'item_text': 'A new item for an existing list'}
        )

        self.assertEqual(Item.objects.count(), 1)
        new_item = Item.objects.first()
        self.assertEqual(new_item.text, 'A new item for an existing list')
        # 确保它挂在了正确的清单名下
        self.assertEqual(new_item.list, correct_list)

    def test_redirects_to_list_view(self):
        other_list = List.objects.create()
        correct_list = List.objects.create()

        response = self.client.post(
            f'/lists/{correct_list.id}/add_item',
            data={'item_text': 'A new item for an existing list'}
        )
        # 确保重定向回了该清单的专属展示页
        self.assertRedirects(response, f'/lists/{correct_list.id}/')