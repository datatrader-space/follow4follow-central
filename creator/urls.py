from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'email-providers', views.EmailProviderViewSet)
router.register(r'proxy-providers', views.ProxyProviderViewSet)
router.register(r'phone-providers', views.PhoneNumberProviderViewSet)
router.register(r'ai-providers', views.AIServiceProviderViewSet)
router.register(r'app-clones', views.AppCloneViewSet, basename='appclone')
router.register(r'account-jobs', views.AccountCreationJobViewSet, basename='accountjob')
urlpatterns = [
    path('', include(router.urls)),
]