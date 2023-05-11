from rest_framework import serializers
from .models import User, Contact, Category, Shop


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'user', 'phone',)
        read_only_fields = ('id',)
        extra_kwargs = {
            'user': {'write_only': True}
        }


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        contacts = ContactSerializer(read_only=True, many=True)
        fields = ('id', 'first_name', 'last_name', 'email', 'company', 'position', 'contacts',)
        read_only_fields = ('id',)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name',)
        read_only_fields = ('id',)


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'name', 'state',)
        read_only_fields = ('id',)

