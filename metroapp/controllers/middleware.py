from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import ObjectDoesNotExist
from metroapp.controllers.views import session_storage


class GuestAccessMiddleware(MiddlewareMixin):
    def process_request(self, request):
        session_id = request.COOKIES.get("session_id")  # Получение session_id из куков
        if session_id:
            username = session_storage.get(session_id)  # Получение user_email из session_storage
            if username:
                try:
                    # Попытка найти пользователя в базе данных
                    request.user = User.objects.get(username=username.decode('utf-8'))
                except ObjectDoesNotExist:
                    request.user = AnonymousUser()
                    print(f"User with email '{username}' not found in database.")
            else:
                request.user = AnonymousUser()
        else:
            request.user = AnonymousUser()
