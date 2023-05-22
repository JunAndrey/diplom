from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.validators import URLValidator
from django.db.models import Q, F, Sum
from django.db import IntegrityError
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
from distutils.util import strtobool

from .models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, Contact, \
    ConfirmEmailToken
from .serializers import UserSerializer, CategorySerializer, ShopSerializer, ProductInfoSerializer, OrderSerializer, \
    OrderItemSerializer, ContactSerializer
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

    # Редактирование данных
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

        if shop_id:
            query = query & Q(shop_id=shop_id)
        if category_id:
            query = query & Q(product__category_id=category_id)

        # фильтруем и отсеиваем дубликаты
        queryset = ProductInfo.objects.filter(query).select_related(
            'shop', 'product__category').prefetch_related(
            'product_parameters__parameter').distinct()
        serializer = ProductInfoSerializer(queryset, many=True)
        return Response(serializer.data)


class BasketView(APIView):
    """
    Класс для работы с корзиной пользователя
    """

    # Получаем корзину
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Login required'}, status=403)
        basket = Order.objects.filter(user_id=request.user.id, state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    # Редактируем корзину
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Login required'}, status=403)
        items_set = request.data.get('items')
        if items_set:
            try:
                items_dict = json_load(items_set)
            except ValueError:
                JsonResponse({'Status': False, 'Error': 'Ошибка в запросе'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                position_created = 0
                for order_item in items_dict:
                    order_item.update({'order': basket.id})
                    serializer = OrderItemSerializer(data=order_item)
                    if serializer.is_valid():
                        try:
                            serializer.save()
                        except IntegrityError as error:
                            return JsonResponse({'Status': False, 'Error': str(error)})
                        else:
                            position_created += 1
                    else:
                        return JsonResponse({'Status': False, 'Error': serializer.errors})
                return JsonResponse({'Status': True, 'Созданы след. позиции': position_created})
        return JsonResponse({'Status': False, 'Error': 'Не указаны все необходимые аргументы'})

    # Удаляем товары из корзины
    def delete(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Login required'}, status=403)
        items_set = request.data.get('items')
        if items_set:
            items_list = items_set.split(',')
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            query = Q()
            position_delete = False
            for item_id in items_list:
                if item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=item_id)
                    position_delete = True
            if position_delete:
                count_deleted = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено  позиций': count_deleted})
        return JsonResponse({'Status': False, 'Error': 'Не указаны все необходимые аргументы'})

    # Редактируем (добавляем) товары в корзине
    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Login required'}, status=403)
        items_set = request.data.get('items')
        if items_set:
            try:
                items_dict = json_load(items_set)
            except ValueError as error:
                JsonResponse({'Status': False, 'Error': 'Неверный запрос'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                position_updated = 0
                for order_item in items_dict:
                    if order_item['id'] == int and type(order_item['quantity']) == int:
                        position_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(
                            quantity=order_item['quantity'])
                return JsonResponse({'Status': True, 'Обновлено позиций': position_updated})
        return JsonResponse({'Status': False, 'Error': 'Не указаны все необходимые аргументы'})


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


class PartnerState(APIView):
    """
    Класс для работы со статусом поставщика
    """

    # получить действующий статус
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": 'Login required'}, status=403)
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Сервис только для магазинов'}, status=403)
        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    # изменить действующий статус
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"Status": False, "Error": 'Login required'}, status=403)
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Сервис только для магазинов'}, status=403)
        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=strtobool(state))
                return JsonResponse({'Status': True})
            except ValueError as error:
                return JsonResponse({'Status': False, 'Error': str(error)})
        return JsonResponse({'Status': False, 'Error': 'Не указаны все необходимые аргументы'})


class PartnerOrders(APIView):
    """
    Класс для получения заказов поставщиками
    """

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Сервис только для магазинов'}, status=403)

        # фильтруем и отсеиваем дубликаты
        order = not Order.objects.filter(ordered_items__product_info__shop__user_id=request.user.id).exclude(
            state='basket').prefetch_related('ordered_items__product_info__product__category',
                                             'ordered_items__product_info__product_parameters__parameter'). \
            select_related('contact').annotate(total_sum=Sum(
            F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)


class ContactView(APIView):
    """
    Класс для работы с контактами покупателей
    """

    # получить контакты
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        contact = Contact.objects.filter(user_id=request.user.id)
        serializer = ContactSerializer(contact, many=True)
        return Response(serializer.data)

    # добавить новый контакт
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        if{'city', 'street', 'phone'}.issubset(request.data):
            request.data._mutable = True
            request.data.update({'user': request.user.id})
            serializer = ContactSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Error': serializer.errors})

        return JsonResponse({'Status': False, 'Error': "Не указаны все необходимые аргументы"})

    # удалить контакт
    def delete(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        items_dict = request.data.get('items')
        if items_dict:
            items_list = items_dict.split(',')
            query = Q()
            contact_deleted = False
            for contact_id in items_list:
                if contact_id.isdigit():
                    query = query | Q(user_id=request.user.id, id=contact_id)
                    contact_deleted = True
            if contact_deleted:
                count_deleted = Contact.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': count_deleted})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # редактировать контакт