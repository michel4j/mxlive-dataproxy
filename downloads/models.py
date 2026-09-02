from django.db import models
import hashlib
from uuid import uuid4


class SecurePath(models.Model):
    """Stores Download Keys for given paths"""
    path = models.CharField(max_length=200)
    key = models.CharField(max_length=200, db_index=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)

    def save(self, *args, **kwargs):
        """
        Create new key and save it to the database if no key is set
        """
        if not self.key:
            h = hashlib.new('ripemd160')  # no successful collision attacks yet
            h.update(self.path.encode('utf-8') + uuid4().bytes)
            self.key = h.hexdigest()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.key

