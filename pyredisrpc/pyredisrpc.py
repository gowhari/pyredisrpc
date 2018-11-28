import json
import uuid
import redis
import logging


logger = logging.getLogger('pyredisrpc')


class Error(Exception):
    '''parent class for all pyredisrpc errors'''
    pass


class BadRequest(Error):
    '''any problem in request from json parse error to method not found raises this error'''
    pass


class CallError(Error):
    '''if any error occur inside called method it raises this error'''
    pass


class Server(object):
    '''redis rpc server'''

    def __init__(self, queue, redis_url='', prefix='pyredisrpc:'):
        '''
        redis_url: url to redis server
        queue: a name to generate server listening queue based on it
        prefix: use as a prefix to generate needed redis keys
        '''
        self.redis = redis.from_url(redis_url)
        self.prefix = prefix
        self.queue = prefix + queue
        self.methods = {}

    def run(self):
        '''
        run main loop of server: receive, parse, call
        '''
        while True:
            _, req_data = self.redis.blpop(self.queue)
            req_data = req_data.decode()
            req_args = self.parse_request(req_data)
            if req_args is None:
                continue
            req_id, method, params = req_args
            self.call_method(req_id, method, params)

    def parse_request(self, req_data):
        '''
        parse request and returns request id, method name and params
        if error, sends error response to client and returns None
        req_data: a string contins json request
        '''
        try:
            req = json.loads(req_data)  # TODO: check unicode data
        except json.JSONDecodeError:
            logger.error('request contains invalid json data: %s', req_data)
            return
        try:
            req_id = req['id']
        except KeyError:
            logger.error('id not found in request: %s', req)
            return
        try:
            method = req['method']
            params = req['params']
        except KeyError as e:
            key = e.args[0]
            logger.error('BadRequest: missing request key: %s', key)
            self.send_response(req_id, None, BadRequest('missing request key', key))
            return
        if method not in self.methods:
            logger.error('BadRequest: method not found: %s', method)
            self.send_response(req_id, None, BadRequest('method not found', method))
            return
        if type(params) != list or len(params) != 2 or type(params[0]) != list or type(params[1]) != dict:
            logger.error('BadRequest: invalid params: %s', params)
            self.send_response(req_id, None, BadRequest('invalid params', params))
            return
        return req_id, method, params

    def call_method(self, req_id, method, params):
        '''
        calls the required client method and send response to client
        if error, sends a CallError response
        '''
        func = self.methods[method]
        params_args = params[0]
        params_kw = params[1]
        try:
            val = func(*params_args, **params_kw)
        except Exception as e:
            logger.exception('CallError: %s', e)
            self.send_response(req_id, None, CallError(repr(e)))
            return
        logger.info('Success: method=%s, params=%s, result=%s', method, params, val)
        self.send_response(req_id, val, None)

    def send_response(self, req_id, result, error):
        '''
        sends a success or error response to client
        result: the result value of called method (any json serializable value), or None if error
        error: an Error object to send to client or None if success
        '''
        if error is not None:
            error = [error.__class__.__name__, error.args]
        result = {'id': req_id, 'result': result, 'error': error}
        key = self.prefix + req_id
        self.redis.rpush(key, json.dumps(result))

    def method(self, f):
        '''
        a decorator to define server methods
        '''
        self.methods[f.__name__] = f


class Client(object):
    '''redis rpc client'''

    def __init__(self, queue, redis_url='', prefix='pyredisrpc:'):
        '''
        redis_url: url to redis server
        queue: a name to generate server listening queue based on it
        prefix: use as a prefix to generate needed redis keys
        '''
        self.redis = redis.from_url(redis_url)
        self.prefix = prefix
        self.queue = prefix + queue

    def call(self, method, params):
        '''
        method: method name to call
        params: a list with exactly two items: [[args], {keywords}]
        '''
        req_id = uuid.uuid4().hex
        req = {'id': req_id, 'method': method, 'params': params}
        self.redis.rpush(self.queue, json.dumps(req))
        key = self.prefix + req_id
        _, response_data = self.redis.blpop(key)
        response = json.loads(response_data.decode())
        if response['error'] is not None:
            self.raise_error(response['error'])
        return response['result']

    def raise_error(self, error):
        '''
        parse and raise received error from server
        error: a list contines two items: [error_name, error_args]
        '''
        err_name, err_args = error
        classes = {'BadRequest': BadRequest, 'CallError': CallError}
        err_class = classes[err_name]
        err = err_class(*err_args)
        raise err

    def __getattr__(self, method):
        def wrap(*args, **kw):
            return self.call(method, [args, kw])
        return wrap
