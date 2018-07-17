import pyredisrpc

server = pyredisrpc.Server('test-queue')

@server.method
def add(a, b):
    return a + b

server.run()
