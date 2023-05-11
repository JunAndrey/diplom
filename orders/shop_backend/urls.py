from django.urls import path
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm
from .views import ProductUpdate, RegisterAccount, AccountVerification, AccountDetails, LoginAccount, CategoryView, \
    ShopView


app_name = "shop_backend"
urlpatterns = [
    path('product', ProductUpdate.as_view(), name='product_update'),
    path('user/register', RegisterAccount.as_view(), name='user-register'),
    path('user/register/verification', AccountVerification.as_view(), name='user-register-verification'),
    path('user/details', AccountDetails.as_view(), name='user-details'),
    path('user/login', LoginAccount.as_view(), name='user-login'),
    path('user/password_reset', reset_password_request_token, name='password-reset'),
    path('user/password_reset/confirm', reset_password_confirm, name='password-confirm'),
    path('categories', CategoryView.as_view(), name='categories'),
    path('shops', ShopView.as_view(), name='shops'),
]