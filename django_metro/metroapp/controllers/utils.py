from django.conf import settings
from django.http import HttpRequest
from django.db.models import Count
from minio import Minio, S3Error

from ..models import Trip, RouteTrip, Route


from django.contrib.auth.models import User


def get_current_user() -> User:
    return User.objects.first()


def get_trip(user: User) -> Trip:
    """ Returns users current trip """
    trip, _ = Trip.objects.get_or_create(user=user, status=Trip.Status.DRAFT)
    return trip


def set_new_trip(request: HttpRequest) -> int:
    cart_trip_id = Trip.objects.create().id
    request.session['cart_trip_id'] = cart_trip_id
    return cart_trip_id


def get_routes(trip: Trip, only_active: bool = True):
    route_ids = RouteTrip.objects.filter(trip=trip).values_list('route',
                                                                flat=True)
    return [Route.objects.get(id=i) for i in route_ids]


def upload_to_minio(file, file_name: str) -> str:
    """
    Загружает файл в MinIO и возвращает URL загруженного файла.
    """
    client = Minio(
        endpoint=settings.MINIO_URL.replace("http://", ""),
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=False
    )
    bucket_name = settings.MINIO_BUCKET_NAME

    # Проверяем, существует ли бакет, если нет — создаём
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)

    # Загружаем файл
    try:
        client.put_object(
            bucket_name=bucket_name,
            object_name=file_name,
            data=file,
            length=-1,  # Используем для файлов неизвестной длины
            part_size=10 * 1024 * 1024,  # Размер части 10 МБ
        )
    except S3Error as e:
        raise RuntimeError(f"Ошибка загрузки в MinIO: {e}")

    # Возвращаем URL файла
    return f"{settings.MINIO_URL}/{bucket_name}/{file_name}"
