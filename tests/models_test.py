from model_bakery import baker
import pytest
from rest_framework.test import APIClient
from shop_backend.models import User, ConfirmEmailToken, Category, Shop


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(first_name='Andrey', last_name='Dzhun', email='jun1969andrey@gmail.com',
                                    password='jskdjdn2421234564$hhv', company='Ecoles', position='manager')


@pytest.fixture
def body():
    return {'first_name': 'Andrey', 'last_name': 'Jun', 'email': 'jun1969andrey@gmail.com',
            'password': 'jskdjdn2421234564$hhv', 'company': 'Ecoles', 'position': 'manager', "contacts": {}}


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
