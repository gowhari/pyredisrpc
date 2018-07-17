pyredisrpc
==========

rpc over redis for python

install
=======

::

    pip install pyredisrpc


usage
=====

server:

.. code:: python

    server = pyredisrpc.Server('test-queue')

    @server.method
    def add(a, b):
        return a + b

    server.run()

client:

.. code:: python

    client = pyredisrpc.Client('test-queue')
    print(client.add(1, 2))
