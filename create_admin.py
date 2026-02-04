import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from usuarios.models import Usuario

def create_admin():
    username = 'admin'
    email = 'admin@example.com'
    password = 'adminpassword123'
    
    if not Usuario.objects.filter(username=username).exists():
        Usuario.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            rol='superusuario'
        )
        print(f"Superuser created successfully!")
        print(f"Username: {username}")
        print(f"Password: {password}")
    else:
        print(f"User '{username}' already exists.")

if __name__ == '__main__':
    create_admin()
