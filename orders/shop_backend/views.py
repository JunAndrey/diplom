from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.validators import URLValidator
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from requests import get
from ujson import loads as json_load
from yaml import load as yaml_load, Loader

from .models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, Contact, \
    ConfirmEmailToken
from .serializers import UserSerializer, CategorySerializer, ShopSerializer
from .signals import user_registered


class RegisterAccount(APIView):
    """
    Для регистрации покупателей
    """

    def post(self, request, *args, **kwargs):
        # проверяем обязательные аргументы
        if {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(request.data):
            errors = {}

            # проверяем пароль на сложность
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_list = []
                for item in password_error:
                    error_list.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_list}})
            else:
                # проверяем данные для уникальности имени пользователя
                request.data._mutable = True
                request.data.update([])
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    # сохраняем пользователя
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    user_registered.send(sender=self.__class__, user_id=user.id)
                    return JsonResponse({'Status': True})
                else:
                    return JsonResponse({'Status': False, 'Error': user_serializer.errors})
        else:
            return JsonResponse({'Status': False, 'Error': 'Не указаны все аргументы'})


class AccountVerification(APIView):
    """
    Класс для подтверждения почтового адреса
    """

    # Регистрация методом POST
    def post(self, request, *args, **kwargs):
        # проверяем обязательные аргументы
        if {'email', 'token'}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Error': 'Пароль или токен неактуальны'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class AccountDetails(APIView):
    """
    Класс для работы c данными пользователя
    """

    # получить данные
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, "Error": 'Login required'}, status=403)
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    # Редактирование данных методом POST
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, "Error": 'Login required'}, status=403)

        # проверяем обязательные аргументы
        if 'password' in request.data:
            # проверяем обязательные аргументы
            errors = {}
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_list = []
                for item in password_error:
                    error_list.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_list}})
            else:
                request.user.set_password(request.data['password'])

        # проверяем остальные данные
        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """

    def post(self, request, *args, **kwargs):
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])
            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    return JsonResponse({'Status': True, 'Token': token.key})
            return JsonResponse({'Status': False, 'Error': 'Ошибка авторизации'})
        return JsonResponse({'Status': False, 'Error': 'Не указаны все необходимые аргументы'})


class CategoryView(ListAPIView):
    """
    Класс для просмотра категорий
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ShopView(ListAPIView):
    """
    Класс для просмотра магазинов
    """
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer


class ProductInfoView(APIView):
    """
    Класс для поиска товаров
    """

    def get(self, request, *args, **kwargs):
        query = Q(shop__state=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

class ProductUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": 'Login required'}, status=403)
        if request.user.type != 'shop':
            return JsonResponse({"Status": False, "Error": 'Сервис только для магазинов'}, status=403)
        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({"Status": False, "Error": str(e)})
            else:
                data_block = get(url).content
                data = yaml_load(data_block, Loader=Loader)
                shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)
                for category in data['categories']:
                    object_on_category, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                    object_on_category.shops.add(shop.id)
                    object_on_category.save()
                ProductInfo.objects.filter(shop_id=shop.id).delete()
                for meaning in data['goods']:
                    product, _ = Product.objects.get_or_create(name=meaning['name'], category_id=meaning['category'])
                    product_info = ProductInfo.objects.create(product_id=product.id, external_id=meaning['id'],
                                                              model=meaning['model'], price=meaning['price'],
                                                              price_rrc=meaning['price_rrc'],
                                                              quantity=meaning['quantity'],
                                                              shop_id=shop.id)
                    for name, value in meaning['parameters'].items():
                        params_object, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(product_info_id=product_info.id,
                                                        parameter_id=params_object.id, value=value)
                return JsonResponse({'Status': True})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
