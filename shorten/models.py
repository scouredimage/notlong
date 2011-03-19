from django.db import models, IntegrityError
from random import sample

from globals import ALPHABET, TOKEN_SIZE, MAX_SAVE_ATTEMPTS
from exceptions import MaxSaveAttemptsExhausted

class Link(models.Model):
  url = models.TextField()
  token = models.CharField(unique=True, max_length=20, db_index=True)
  ip = models.IPAddressField(db_index=True)
  date = models.DateTimeField(auto_now_add=True, db_index=True)
  algorithm = models.CharField(max_length=10, default='sample')
  visits = models.PositiveIntegerField(default=0)

  class Meta:
    db_table = 'links'
    ordering = ['-date', '-id']
    get_latest_by = 'date'

  def _token(self):
    return ''.join(sample(ALPHABET, TOKEN_SIZE))

  def save(self, *args, **kwargs):
    if self.token:
      super(Link, self).save(*args, **kwargs)
    else:
      attempt = 1
      while attempt < MAX_SAVE_ATTEMPTS:
        self.token = self._token()
        try:
          super(Link, self).save(*args, **kwargs)
          break
        except IntegrityError:
          attempt += 1
      else:
        raise MaxSaveAttemptsExhausted(self.url, attempt)

  @models.permalink
  def get_absolute_url(self):
    return ('shorten.views.follow', [self.token])

  def __unicode__(self):
    return u'%s' % self.url

class Visit(models.Model):
  link = models.ForeignKey('Link')
  date = models.DateTimeField(auto_now_add=True, db_index=True)
  ip = models.IPAddressField(db_index=True)
  referer = models.CharField(null=True, blank=True, max_length=500)

  class Meta:
    db_table = 'visits'
    ordering = ['-date', '-id']
    get_latest_by = 'date'
    order_with_respect_to = 'link'

  def __unicode__(self):
    return u'%s:%s:%s' % (self.link, self.date, self.ip)

