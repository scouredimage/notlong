from django.http import HttpResponse, Http404, HttpResponsePermanentRedirect
from django.utils import simplejson
from django.views.decorators.http import require_http_methods
from django.contrib.sites.models import Site
from django.db.models import F

from urlparse import urlparse
from urllib import urlencode, urlopen
from urllib2 import HTTPRedirectHandler, HTTPCookieProcessor, Request, \
                    HTTPError, build_opener

from globals import CONNECTION_TIMEOUT
from models import Link, Visit
from exceptions import MaxSaveAttemptsExhausted, TargetNotValid
from surblclient import surbl

import logging, logconfig
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('shorten')

class Response(dict):
  def __init__(self):
    super(Response, self).__init__()
    self['statusCode'] = ''
    self['results'] = None

def server_error(request):
  response = Response()
  response.update({'errorCode': 500,
                   'errorMessage': 'UNKNOWN_ERROR'})
  return HttpResponse(simplejson.dumps(response),
                      mimetype='application/json')

def open(url):
  logger.debug('Opening: %s' % url)

  headers = dict()
  headers['User-Agent'] = 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; ' \
                          'rv:1.9.2.13) Gecko/20101203 Firefox/3.6.13'

  opener = build_opener(HTTPRedirectHandler(), HTTPCookieProcessor())

  try:
    result = opener.open(Request(url, headers=headers),
                         timeout=CONNECTION_TIMEOUT)

    code = result.getcode()
    logger.debug('Response code opening %s: %d' % (url, code))

    if code < 200 or code >= 300:
      raise TargetNotValid(code=code)

    return result.geturl()

  except HTTPError, err:
    logger.debug('Error opening %s: %s' % (url, str(err)))
    raise TargetNotValid(msg=str(err))

@require_http_methods(['GET', 'POST'])
def shorten(request):
  querydict = request.GET if request.method == 'GET' else request.POST

  url = querydict.get('longUrl', None)
  logger.debug('Shorten: %s' % url)

  response = Response()
  if not url:
    response.update({'errorCode': 404,
                     'errorMessage': 'MISSING_ARG_LONGURL'})
  else:
    parsed = urlparse(url)
    logger.debug('Parsed %s: (scheme=%s, netloc=%s)' % \
                 (url, parsed.scheme, parsed.netloc))

    if not parsed.netloc:
      response.update({'errorCode': 500,
                       'errorMessage': 'INVALID_URI'})
    else:
      try:
        target = open(url)
        logger.debug('Target for %s: %s' %(url, target))

        parsed = urlparse(target)
        domain = '%s://%s' % (parsed.scheme or 'http', parsed.netloc)

        if domain in surbl:
          logger.warn('Attempt to save blacklisted domain: %s from ip: %s' % \
                      (domain, request.META.get('REMOTE_ADDR')))
          response.update({'errorCode': 500,
                           'errorMessage': 'DOMAIN_BLACKLISTED'})

        else:
          link = Link(url=target, ip=request.META.get('REMOTE_ADDR'))

          try:
            link.save()
            logger.info('Assigned token: %s for url: %s' % (link.token, url))

            permalink = 'http://%s%s' % (Site.objects.get_current().domain,
                                         link.get_absolute_url())
            logger.debug('Permalink for %s: %s' % (url, permalink))

            response.update({'errorCode': 0,
                             'errorMessage': '',
                             'results' : {url: {'userHash': link.token,
                                                'hash': link.token,
                                                'shortKeywordUrl': '',
                                                'shortCNAMEUrl': permalink,
                                                'shortUrl': permalink}},
                             'statusCode': 'OK'})

          except MaxSaveAttemptsExhausted, err:
            logger.error('Saving url: %s failed! Attempts=%d' % \
                         (url, err.attempts))
            response.update({'errorCode': 403,
                             'errorMessage': 'RATE_LIMIT_EXCEEDED'})

      except TargetNotValid, err:
        logger.warn('Attempt to shorten invalid URL: %s' % url)
        response.update({'errorCode': 500,
                         'errorMessage' : 'INVALID_URI'})

  callback = querydict.get('callback')
  if callback:
    return HttpResponse('%s(%s)' % (callback, simplejson.dumps(response)),
                        mimetype='text/javascript')
  else:
    return HttpResponse(simplejson.dumps(response),
                        mimetype='application/json')

@require_http_methods(['GET',])
def follow(request, token):
  logger.debug('Follow: %s' % token)

  try:
    link = Link.objects.get(token=token)
  except Link.DoesNotExist:
    raise Http404()

  ip = request.META.get('REMOTE_ADDR')
  referer = request.META.get('HTTP_REFERER')

  visit = Visit(link=link, ip=ip, referer=referer)
  visit.save()

  link.visits = F('visits') + 1
  link.save()

  return HttpResponsePermanentRedirect(link.url)

@require_http_methods(['GET',])
def expand(request):
  response = Response()

  try:
    parsed = urlparse(request.GET['shortUrl'])
    token = parsed.path[1:]
    logger.debug('Expand: %s' % token)
  except KeyError:
    response.update({'errorCode': 201,
                     'errorMessage': 'Missing parameter shortUrl'})
  else:
    try:
      link = Link.objects.get(token=token)

      permalink = 'http://%s%s' % (Site.objects.get_current().domain,
                                   link.get_absolute_url())

      response.update({'errorCode': 0,
                       'errorMessage': '',
                       'results': {token: {'longUrl': link.url}},
                       'statusCode': 'OK'})

    except Link.DoesNotExist:
      response.update({'errorCode': 1203,
                       'errorMessage': 'No info available for requested document.'})

  callback = request.GET.get('callback')
  if callback:
    return HttpResponse('%s(%s)' % (callback, simplejson.dumps(response)),
                        mimetype='text/javascript')
  else:
    return HttpResponse(simplejson.dumps(response),
                        mimetype='application/json')


