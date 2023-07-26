from model_bakery import baker
import pytest
import requests
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
import shop_backend.models
from shop_backend.models import User, ConfirmEmailToken


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
def authorisation():
    return {'Authorization': 'Token 9d0cd9c568d0c1fcd259afadacf597d70b2665b2'}


@pytest.mark.django_db
def test_users(client, body):
    count = User.objects.count()
    response = client.post('/api/v1/user/register', data=body)
    user = User.objects.get(first_name='Andrey')
    assert User.objects.count() == count + 1
    assert response.status_code == 200
    assert user.first_name == 'Andrey'
    assert user.last_name == 'Jun'
    assert user.company == 'Ecoles'


@pytest.mark.django_db
def test_AccountVerification(client, user):
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
    data = {'email': 'jun1969andrey@gmail.com', 'token': token.key}
    response = client.post('/api/v1/user/register/verification', data=data)
    assert token.user.is_active == True
    assert response.status_code == 200


@pytest.mark.django_db
def test_LoginAccount(client, user):
    data = {"email": user.email, "password": "jskdjdn2421234564$hhv"}
    response = client.post('/api/v1/user/login', data=data)
    token = Token.objects.get(user=user)
    assert response.status_code == 200
    assert token



# @pytest.mark.django_db
# def test_AccountDetails(client, user):
#     response = client.get('/api/v1/user/details', user_id=user.id)
#     print(response.json())
#     assert response.status_code == 200

