class MaxSaveAttemptsExhausted(Exception):
  def __init__(self, url, attempts):
    self.url = url
    self.attempts = attempts

  def __str__(self):
    return 'Exceeded maximum save attempts: %d' % self.attempts

class TargetNotValid(Exception):
  def __init__(self, msg=None, code=None):
    self.msg = msg
    self.code = code

  def __str__(self):
    if self.msg:
      return self.msg
    else:
      return 'Target responded with non-success code: %d' % self.code

