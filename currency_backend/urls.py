"""currency_backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from . import view, scheme, rate, plan


def path_c(pt, func):
    return path("currency_backend/" + pt, func)


urlpatterns = [
    path_c('test', plan.test),
    path('', view.hello),
    path('', view.hello),
    path_c('', view.hello),
    path_c('login', view.login),
    path_c('getIdentity', view.getIdentity),
    path_c('logout', view.logout),
    path_c('register', view.register),
    path_c('getUserInfo', view.getUserInfo),
    path_c('changeUserInfo', view.changeUserInfo),
    path_c('resetPassword', view.resetPassword),
    path_c('resetPasswordUser', view.resetPasswordUser),
    # path_c('getUserList', view.getUserList),
    path_c('changeUserStatus', view.changeUserStatus),
    path_c('changePassword', view.changePassword),
    path_c('getCaptcha', view.getCaptcha),
    path_c('uploadFile', view.uploadFile),
    path_c('getSchemeMenu', scheme.getSchemeMenu),
    path_c('getSchemeOverview', scheme.getSchemeOverview),
    path_c('addScheme', scheme.addScheme),
    path_c('getCoinInfo', rate.getCoinInfo),
    path_c('getSchemeChart', scheme.getSchemeChart),
    path_c('getSchemeAccount', scheme.getSchemeAccount),
    path_c('getSchemeLogs', scheme.getSchemeLogs),
    path_c('waitGetSchemeAddress', scheme.waitGetSchemeAddress),
    path_c('editSchemeDesc', scheme.editSchemeDesc),
    path_c('waitSchemeLogs', scheme.waitSchemeLogs),
    path_c('withdrawCoin', scheme.withdrawCoin),
    path_c('addAddressBook', scheme.addAddressBook),
    path_c('deleteAddressBook', scheme.deleteAddressBook),
    path_c('getInvestPlan', scheme.getInvestPlan),
    path_c('newInvestPlan', plan.newInvestPlan),
    #path_c('newInvestPlan', scheme.newInvestPlan),
]

handler404 = view.S04
handler500 = view.S500
