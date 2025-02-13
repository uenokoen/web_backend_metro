import segno
import base64
from io import BytesIO
def generate_trip_qr(trip, routes, moderator):
    """
    Генерация QR-кода для поездки с учетом её деталей.
    """
    info = f"Поездка №{trip.id}\nСтатус: {trip.status}\nМодератор: {moderator.username}\n\n"

    total_duration = 0
    route_info = []

    for route_trip in routes:
        route = route_trip.route  # Получаем объект маршрута
        duration = route_trip.duration
        total_duration += duration
        route_info.append(f"{route.origin} → {route.destination} ({duration} мин.)")

    info += "Маршруты:\n"
    info += "\n".join(route_info)
    info += f"\n\nОбщая длительность: {total_duration} мин."

    ended_at_str = trip.ended_at.strftime('%Y-%m-%d %H:%M:%S') if trip.ended_at else "Не завершена"
    info += f"\nДата завершения: {ended_at_str}"

    # Генерация QR-кода
    qr = segno.make(info)
    buffer = BytesIO()
    qr.save(buffer, kind='png')
    buffer.seek(0)

    # Конвертация изображения в base64
    qr_image_base64 = base64.b64encode(buffer.read()).decode('utf-8')

    return qr_image_base64
