from django.contrib.auth.models import User


class CreatorSingleton:
    _instance = None

    @staticmethod
    def get_creator():
        if CreatorSingleton._instance is None:
            CreatorSingleton._instance = User.objects.get(id=1)
        return CreatorSingleton._instance

    @staticmethod
    def get_moderator():
        if CreatorSingleton._instance is None:
            CreatorSingleton._instance = User.objects.get(id=2)
        return CreatorSingleton._instance
