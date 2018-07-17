import pyredisrpc

client = pyredisrpc.Client('test-queue')
print(client.add(1, 2))
