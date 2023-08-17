from model_bakery import baker
import pytest
from rest_framework.test import APIClient
from shop_backend.models import User, ConfirmEmailToken, Category, Shop, ProductInfo, Product, Parameter, Contact, \
    Order, ProductParameter


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(first_name='Andrey', last_name='Dzhun', email='jun1969andrey@gmail.com',
                                    password='jskdjdn2421234564$hhv', company='Ecoles', position='manager', type='shop')


# @pytest.fixture
# def product_factory():
#     return ProductInfo.objects.create(model='Iphone14', external_id=1234, quantity=14, price=75000,
#                                              price_rrc=85000, product_id=product.id, shop_id=shops[0].pk)


@pytest.fixture
def body():
    return {'first_name': 'Andrey', 'last_name': 'Jun', 'email': 'jun1969andrey@gmail.com',
            'password': 'jskdjdn2421234564$hhv', 'company': 'Ecoles',
            'position': 'manager', "contacts": {}, 'type': 'shop'}


@pytest.fixture
def category_factory():
    def factory(*args, **kwargs):
        return baker.make(Category, *args, **kwargs)

    return factory


@pytest.fixture
def shops_factory():
    def factory_2(*args, **kwargs):
        return baker.make(Shop, *args, **kwargs)

    return factory_2


@pytest.fixture
def token_return(user, client):
    data = {"email": user.email, "password": "jskdjdn2421234564$hhv"}
    response = client.post('/api/v1/user/login', data=data)
    headers = {'Authorization': 'Token ' + response.json()['Token']}
    return headers


@pytest.mark.django_db
def test_users(client, body):
    count = User.objects.count()
    response = client.post('/api/v1/user/register', data=body)
    user = User.objects.get(first_name='Andrey')
    assert User.objects.count() == count + 1
    assert response.status_code == 200
    assert user.first_name == body['first_name']
    assert user.last_name == body['last_name']
    assert user.company == body['company']


@pytest.mark.django_db
def test_AccountVerification(client, user):
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
    data = {'email': 'jun1969andrey@gmail.com', 'token': token.key}
    response = client.post('/api/v1/user/register/verification', data=data)
    assert token.user.is_active == True
    assert response.status_code == 200


@pytest.mark.django_db
def test_AccountDetail(token_return, body, client):
    response = client.get('/api/v1/user/details', headers=token_return)
    resp_json = response.json()
    assert response.status_code == 200
    assert resp_json['first_name'] == body['first_name']
    data = {'first_name': 'Andrey', 'last_name': 'Junior', 'email': 'junior_69@gmail.com'}
    response_1 = client.post('/api/v1/user/details', headers=token_return, data=data)
    resp_json_1 = response_1.json()
    assert response_1.status_code == 200
    assert resp_json_1['email'] == data['email']


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
def test_ProductInfoView(client, shops_factory, category_factory):
    shops = shops_factory(_quantity=3)
    category = category_factory(_quantity=4)
    product = Product.objects.create(name='phone', category_id=category[0].id)
    productinfo = ProductInfo.objects.create(model='Iphone14', external_id=1234, quantity=14, price=75000,
                                             price_rrc=85000, product_id=product.id, shop_id=shops[0].id)
    response = client.get('/api/v1/product', kwargs={'shop_id': productinfo.shop_id,
                                                     'category_id': category[0].id})
    data = response.json()
    assert productinfo.model == data[0]['model']
    assert response.status_code == 200


# @pytest.mark.django_db
# def test_BasketView(token_return, body, client, user, shops_factory, category_factory):
#     shop = shops_factory(_quantity=2)
#     category = category_factory(_quantity=2)
#     product = Product.objects.create(name='phone', category_id=category[0].pk)
#     parameter = Parameter.objects.create(name='color')
#     print(f'param', parameter.__dict__)
#     print(f'product', product.__dict__)
#     contact = Contact.objects.create(user_id=user.id, city='Moskow', street='Lenin', house=7, phone='+7777777777')
#     product_info = ProductInfo.objects.create(model='Iphone14', external_id=1234, quantity=14, price=75000,
#                                               price_rrc=85000, product_id=product.id, shop_id=shop[0].pk)
#     product_parameter = ProductParameter.objects.create(product_info_id=product_info.id,
#                                                         parameter_id=parameter.pk, value='black')
#     print(f'prod', product_info.__dict__)
#     order = Order.objects.create(user_id=user.id, state='basket', contact_id=contact.pk)
#     print(f'order', order.__dict__)
#     data = {'order': order.id, 'shop': shop[0].pk, 'quantity': 2, 'product_info': product_info.id}
#     # data = {'items': {"id": 2}}
#     response_post = client.post('/api/v1/basket', headers=token_return, data=data)
#     print(f'post', response_post.json())
#     assert response_post.status_code == 200
#     # assert response_post.json()['Status'] == True
#     response_get = client.get('/api/v1/basket', headers=token_return)
#     print(f'get', response_get.json())
#     assert response_get.status_code == 201


@pytest.mark.django_db
def test_PartnerState(client, token_return, user):
    count = Shop.objects.count()
    shop = Shop.objects.create(user_id=user.id, name='Store')
    response_get = client.get('/api/v1/partner/state', headers=token_return)
    assert Shop.objects.count() == count + 1
    assert response_get.json()['name'] == shop.name
    assert response_get.status_code == 200
    data = {'state': "true"}
    response_post = client.post('/api/v1/partner/state', headers=token_return, data=data)
    assert shop.state == True
    assert response_post.status_code == 200


@pytest.mark.django_db
def test_PartnerOrders(client, token_return, user):
    shop = Shop.objects.create(user_id=user.id, name='Store', state=True)
    response_get = client.get('/api/v1/partner/orders', headers=token_return)
    print(response_get.json())
    assert response_get.status_code == 201
