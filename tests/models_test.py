from model_bakery import baker
import pytest
from rest_framework.test import APIClient
from shop_backend.models import User, ConfirmEmailToken, Category, Shop, ProductInfo, Product, Parameter, Contact, \
    Order, ProductParameter, OrderItem
import ujson
from yaml import load as yaml_load, Loader


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(first_name='Andrey', last_name='Dzhun', email='jun1969andrey@gmail.com',
                                    password='jskdjdn2421234564$hhv', company='Ecoles', position='manager', type='shop')


@pytest.fixture
def contact(user):
    return Contact.objects.create(user_id=user.id, city='Moskow', street='Lenin', house=7, phone='+7777777777')


@pytest.fixture
def body():
    return {'first_name': 'Andrey', 'last_name': 'Jun', 'email': 'jun1969andrey@gmail.com',
            'password': 'jskdjdn2421234564$hhv', 'company': 'Ecoles',
            'position': 'manager', "contacts": {}, 'type': 'shop'}


@pytest.fixture
def token_return(user, client):
    data = {"email": user.email, "password": "jskdjdn2421234564$hhv"}
    response = client.post('/api/v1/user/login', data=data)
    headers = {'Authorization': 'Token ' + response.json()['Token']}
    return headers


@pytest.fixture
def shop(user):
    return Shop.objects.create(user_id=user.id, url="https://Store777.ru", name="Store", state=True)


@pytest.fixture
def category(shop):
    categories = Category.objects.create(name='smart')
    categories.shops.add(shop)
    return categories


@pytest.fixture
def product(category):
    return Product.objects.create(name='phone', category=category)


@pytest.fixture
def productinfo(shop, product):
    return ProductInfo.objects.create(model='Iphone 14', product=product, shop=shop,
                                      quantity=5, external_id=987, price=80000, price_rrc=85000)


@pytest.fixture
def parameter(productinfo):
    parameter = Parameter.objects.create(name='condition')
    return ProductParameter.objects.create(product_info=productinfo, parameter=parameter, value='new')


@pytest.fixture
def order(user, contact):
    return Order.objects.create(user_id=user.id, state='basket', contact_id=contact.id)


@pytest.fixture
def order_item(order, productinfo, shop):
    return OrderItem.objects.create(order=order, product_info=productinfo, quantity=3, shop=shop)


@pytest.mark.django_db
def test_users(client, body):
    count = User.objects.count()
    client.post('/api/v1/user/register', data=body)
    user = User.objects.get(first_name='Andrey')
    assert User.objects.count() == count + 1
    assert user.first_name == body['first_name']
    assert user.last_name == body['last_name']
    assert user.company == body['company']


@pytest.mark.django_db
def test_AccountVerification(client, user):
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
    data = {'email': 'jun1969andrey@gmail.com', 'token': token.key}
    client.post('/api/v1/user/register/verification', data=data)
    assert token.user.is_active is True


@pytest.mark.django_db
def test_AccountDetail(token_return, body, client):
    response = client.get('/api/v1/user/details', headers=token_return)
    resp_json = response.json()
    assert resp_json['first_name'] == body['first_name']
    data = {'first_name': 'Andrey', 'last_name': 'Junior', 'email': 'junior_69@gmail.com'}
    response_1 = client.post('/api/v1/user/details', headers=token_return, data=data)
    resp_json_1 = response_1.json()
    assert resp_json_1['email'] == data['email']


@pytest.fixture
def category_factory():
    def factory(*args, **kwargs):
        return baker.make(Category, *args, **kwargs, make_m2m=True)

    return factory


@pytest.fixture
def shops_factory():
    def factory_2(*args, **kwargs):
        return baker.make(Shop, *args, **kwargs, make_m2m=True)

    return factory_2


@pytest.mark.django_db
@pytest.mark.parametrize("test_input,expected", [('/api/v1/categories', 200),
                                                 ('/api/v1/shops', 200)])
def test_CategoryShopView(test_input, expected, client):
    response = client.get(test_input)
    assert response.status_code == expected


@pytest.mark.django_db
def test_get_categories(category_factory, client):
    category = category_factory(_quantity=5)
    response = client.get('/api/v1/categories')
    data = response.json()
    assert len(data['results']) == len(category)
    assert data['count'] == len(category)


@pytest.mark.django_db
def test_get_shops(shops_factory, client):
    shops = shops_factory(_quantity=4)
    response = client.get('/api/v1/shops')
    data = response.json()
    assert len(data['results']) == len(shops)
    sorted_data = sorted(data['results'], key=lambda item: item['id'])
    for ind, item in enumerate(sorted_data):
        assert item['name'] == shops[ind].name


@pytest.mark.django_db
def test_get_categories(category_factory, client):
    category = category_factory(_quantity=5)
    response = client.get('/api/v1/categories')
    data = response.json()
    assert len(data['results']) == len(category)
    sorted_data = sorted(data['results'], key=lambda item: item['id'])
    for ind, item in enumerate(sorted_data):
        assert item['name'] == category[ind].name


@pytest.mark.django_db
def test_ProductInfoView(client, shop, category, product, productinfo):
    response = client.get('/api/v1/product', kwargs={'shop_id': productinfo.shop_id,
                                                     'category_id': category.id})
    data = response.json()
    assert productinfo.model == data[0]['model']
    assert productinfo.quantity == data[0]['quantity']


@pytest.mark.django_db(transaction=True)
def test_BasketView(token_return, order, client, shop, productinfo):
    response_get_1 = client.get('/api/v1/basket', headers=token_return)
    res_get_1 = response_get_1.json()
    assert res_get_1[0]['total_sum'] is None
    data = {"items": ujson.dumps([{"order": order.id, "product_info": productinfo.id, "shop": shop.id, "quantity": 5}])}
    response_post = client.post('/api/v1/basket', headers=token_return, data=data)
    res_post = response_post.json()
    assert res_post['Status'] is True
    assert res_post['Создано позиций'] == len(ujson.loads(data["items"]))
    response_get = client.get('/api/v1/basket', headers=token_return)
    res_get = response_get.json()
    assert res_get[0]['ordered_items'][0]['quantity'] == ujson.loads(data["items"])[0]['quantity']
    data_2 = {"items": ujson.dumps([{"id": order.id, "product_info": productinfo.id, "shop": shop.id, "quantity": 2}])}
    response_put = client.put('/api/v1/basket', headers=token_return, data=data_2)
    res_put = response_put.json()
    assert res_put['Status'] is True
    assert res_put['Обновлено позиций'] == len(ujson.loads(data_2["items"]))
    data_3 = {"items": f"{order.id}"}
    response_delete = client.delete('/api/v1/basket', headers=token_return, data=data_3)
    res_del = response_delete.json()
    assert res_del['Status'] is True
    assert res_del['Удалено  позиций'] == len(data_3["items"])


@pytest.mark.django_db
def test_ProductUpdate(client, token_return):
    with open('shop1.yaml') as f:
        data_yaml = yaml_load(f, Loader=Loader)
    print(f'data_yaml', data_yaml)
    response_post = client.post('/api/v1/product/update', headers=token_return, data=data_yaml)
    res_post = response_post.json()
    assert res_post['Status'] is True
    print(f'res_post', res_post)


@pytest.mark.django_db
def test_PartnerState(client, token_return, user):
    count = Shop.objects.count()
    shop = Shop.objects.create(user_id=user.id, name='Store')
    response_get = client.get('/api/v1/partner/state', headers=token_return)
    assert Shop.objects.count() == count + 1
    assert response_get.json()['name'] == shop.name
    data = {'state': "true"}
    client.post('/api/v1/partner/state', headers=token_return, data=data)
    assert shop.state is True


@pytest.mark.django_db
def test_PartnerOrders(client, token_return, shop, order, order_item, productinfo):
    response_get = client.get('/api/v1/partner/orders', headers=token_return,
                              kwargs={"order": order_item})
    print(f'response_get', response_get.json())
    assert response_get.status_code == 201


@pytest.mark.django_db
def test_ContactView(client, token_return):
    count = Contact.objects.count()
    data = {'city': 'Petersburg', 'street': 'Leninskiy prosp.', 'house': 7, 'apartment': 34, 'phone': '+79118888888'}
    response_post = client.post('/api/v1/user/contact', headers=token_return, data=data)
    res_post = response_post.json()
    count_2 = Contact.objects.count()
    assert count_2 == count + 1
    assert res_post["Status"] is True
    response_get = client.get('/api/v1/user/contact', headers=token_return)
    res_get = response_get.json()
    assert res_get[0]['city'] == data['city']
    data_2 = {"id": str(res_get[0]['id']), "city": 'Saint-Petersburg'}
    response_put = client.put('/api/v1/user/contact', headers=token_return, data=data_2)
    assert response_put.json()['Status'] is True
    response_get_2 = client.get('/api/v1/user/contact', headers=token_return)
    res_get_2 = response_get_2.json()
    assert res_get_2[0]['city'] == data_2['city']
    data_3 = {"items": f"{data_2['id']}"}
    response_delete = client.delete('/api/v1/user/contact', headers=token_return, data=data_3)
    res_del = response_delete.json()
    assert res_del['Удалено объектов'] == len(data_3['items'])


@pytest.mark.django_db(transaction=True)
def test_OrderView(client, token_return, order_item, contact):
    data1 = {'id': str(order_item.id), 'contact': contact.id}
    response_post = client.post('/api/v1/order', headers=token_return, data=data1)
    res_post = response_post.json()
    assert res_post['Status'] is True
    response_get = client.get('/api/v1/order', headers=token_return)
    res_get = response_get.json()
    assert order_item.product_info.__dict__['price'] * order_item.__dict__['quantity'] == res_get[0]['total_sum']


