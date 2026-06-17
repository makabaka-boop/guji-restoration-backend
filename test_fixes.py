import requests
import json

base_url = 'http://localhost:8112/api'

def login(username, password):
    resp = requests.post(f'{base_url}/auth/login/', json={'username': username, 'password': password})
    return resp.json()['access']

admin_headers = {'Authorization': f'Bearer {login("admin", "admin123")}'}
restorer_headers = {'Authorization': f'Bearer {login("restorer", "restorer123")}'}
reviewer_headers = {'Authorization': f'Bearer {login("reviewer", "reviewer123")}'}

print("=" * 60)
print("  验证修复1：同一本书只能有一个未完成工单")
print("=" * 60)

# 先查一下BK001有没有未完成工单
resp = requests.get(f'{base_url}/work-orders/', params={'book_no': 'BK001', 'status': 'pending_receive'}, headers=admin_headers)
print(f"BK001 待接收工单数: {resp.json()['count']}")

# 再查所有状态的
resp = requests.get(f'{base_url}/work-orders/', params={'book_no': 'BK001'}, headers=admin_headers)
print(f"BK001 总工单数: {resp.json()['count']}")

# 创建第一个工单
create_data = {
    'book': 1,
    'work_station': 1,
    'responsible_person': 1,
    'restorer': 2,
    'reviewer': 3,
    'review_interval_hours': 24,
    'damage_description': '测试唯一性1'
}
resp = requests.post(f'{base_url}/work-orders/', json=create_data, headers=admin_headers)
print(f"\n第一次创建工单: {resp.status_code}")
if resp.status_code == 201:
    order1_id = resp.json()['id']
    print(f"  成功: {resp.json()['order_no']}")
else:
    print(f"  失败: {resp.json()}")

# 再创建一个
resp2 = requests.post(f'{base_url}/work-orders/', json=create_data, headers=admin_headers)
print(f"第二次创建工单(同书册): {resp2.status_code}")
if resp2.status_code != 201:
    print(f"  错误: {resp2.json()}")
else:
    print(f"  警告：{resp2.json()['order_no']}")

print("\n" + "=" * 60)
print("  验证修复2：管理员不能提交修护记录")
print("=" * 60)

# 先创建一个新工单用于测试
create_data2 = {
    'book': 2,
    'work_station': 2,
    'responsible_person': 2,
    'restorer': 2,
    'reviewer': 3,
    'review_interval_hours': 48,
    'damage_description': '测试权限'
}
resp = requests.post(f'{base_url}/work-orders/', json=create_data2, headers=admin_headers)
order2_id = resp.json()['id']
print(f"创建测试工单: {resp.json()['order_no']}")

# 管理员尝试接收
resp = requests.post(f'{base_url}/work-orders/{order2_id}/receive/', headers=admin_headers)
print(f"\n管理员接收工单: {resp.status_code}")
if resp.status_code == 403:
    print("  ✅ 正确：管理员被禁止")
else:
    print(f"  ⚠️  结果: {resp.json()}")

# 修护师接收
resp = requests.post(f'{base_url}/work-orders/{order2_id}/receive/', headers=restorer_headers)
print(f"修护师接收工单: {resp.status_code}")
if resp.status_code == 200:
    print(f"  ✅ 正确：修护师可以接收，当前状态: {resp.json()['status_name']}")
else:
    print(f"  ⚠️  结果: {resp.json()}")

# 管理员尝试提交修护
repair_data = {
    'has_page_separation': True,
    'process_remark': '管理员尝试提交'
}
resp = requests.post(f'{base_url}/work-orders/{order2_id}/submit_repair/', json=repair_data, headers=admin_headers)
print(f"\n管理员提交修护: {resp.status_code}")
if resp.status_code == 403:
    print("  ✅ 正确：管理员被禁止")
else:
    print(f"  ⚠️  结果: {resp.json()}")

# 修护师提交修护
resp = requests.post(f'{base_url}/work-orders/{order2_id}/submit_repair/', json=repair_data, headers=restorer_headers)
print(f"修护师提交修护: {resp.status_code}")
if resp.status_code == 200:
    print(f"  ✅ 正确：修护师可以提交，当前状态: {resp.json()['status_name']}")
else:
    print(f"  ⚠️  结果: {resp.json()}")

print("\n" + "=" * 60)
print("  验证修复3：复核间隔按工单自身设定")
print("=" * 60)

# 完成压平进入待复核
resp = requests.post(f'{base_url}/work-orders/{order2_id}/complete_pressing/', headers=restorer_headers)
print(f"完成压平: {resp.status_code} - 当前状态: {resp.json()['status_name']}")
print(f"工单设定的复核间隔: {resp.json()['review_interval_hours']} 小时")

# 查看预警
resp = requests.get(f'{base_url}/alerts/', headers=admin_headers)
data = resp.json()
print(f"\n当前预警总数: {data['total']}")
overdue = [a for a in data['alerts'] if a['type'] == 'overdue_review']
print(f"其中复核超期预警: {len(overdue)} 条")
for a in overdue:
    print(f"  - {a['message']}")

print("\n" + "=" * 60)
print("  所有验证完成")
print("=" * 60)
