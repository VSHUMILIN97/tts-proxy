from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    name = 'projects'

    def ready(self):
        """ Make imports and everything what should before the app starts """
        import projects.signals  # noqa
