__all__ = ["create_admin_app"]


def create_admin_app():
    from .app import create_admin_app as _create_admin_app

    return _create_admin_app()
