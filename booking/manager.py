from django.contrib.auth.models import BaseUserManager

class BaseUser(BaseUserManager):
    def create_user(self,email,username,password):
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            username = username,
            password = password
        )
        user.set_password(password)
        user.save(using = self._db)
        return user
    
    def create_admin(self,email,username,password):
        user = self.create_user(
            email=email,
            username=username,
            password=password
        )
        user.is_admin = True
        user.save(using = self._db)
        return user
    
    def create_superuser(self,email,username,password):
        user = self.create_user(
            email=email,
            username=username,
            password=password
        )
        user.is_verified = True
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.role = False
        user.save(using = self._db)
        return user
    
    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True
    