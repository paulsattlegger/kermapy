import asyncio

from tests.test_kermapy import KermaTestCase, Client


class Task2TestCase(KermaTestCase):

    async def test_getSameObject(self):
        # If Grader 1 sends a new valid transaction object and then requests the same object, Grader 1 should receive
        # the object.
        client = await Client.new_established()
        await client.write(b'{"type":"object","object":{"height":1,"outputs":['
                           b'{"pubkey":"62b7c521cd9211579cf70fd4099315643767b96711febaa5c76dc3daf27c281c",'
                           b'"value":50000000000000}],"type":"transaction"}}\n')
        await client.write(
            b'{"type":"getobject","objectid":"48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d05c53802b69c7cd9fb"}\n')
        response = await client.readline()
        self.assertIn(
            b'"62b7c521cd9211579cf70fd4099315643767b96711febaa5c76dc3daf27c281c"', response)
        self.assertIn(b'"type":"object"', response)
        await client.close()

    async def test_getSameObject_2(self):
        # If Grader 1 sends a new valid transaction object and then requests the same object, Grader 1 should receive
        # the object.
        client = await Client.new_established()
        await client.write(b'{"type":"object","object":{"height":1,"outputs":['
                           b'{"pubkey":"62b7c521cd9211579cf70fd4099315643767b96711febaa5c76dc3daf27c281c",'
                           b'"value":50000000000000}],"type":"transaction"}}\n')

        await client.write(b'{"type":"object","object":{"inputs":['
                           b'{"outpoint":{"index":0,"txid":"48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d0'
                           b'5c53802b69c7cd9fb"},"sig":"d51e82d5c121c5db21c83404aaa3f591f2099bccf731208c4b0b'
                           b'676308be1f994882f9d991c0ebfd8fdecc90a4aec6165fc3440ade9c83b043cba95b2bba1d0a"}],'
                           b'"outputs":[{"pubkey":"228ee807767047682e9a556ad1ed78dff8d7edf4bc2a5f4fa02e4634cfcad7e0",'
                           b'"value":49000000000000}],"type":"transaction"}}\n')

        await client.write(
            b'{"type":"getobject","objectid":"d33ac384ea704025a6cac53f669c8e924eff7205b0cd0d6a231f0881b6265a8e  "}\n')
        response = await client.readline()
        self.assertIn(
            b'"48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d05c53802b69c7cd9fb"', response)
        self.assertIn(b'"type":"object"', response)
        await client.close()

    async def test_getSameObjectOtherClient(self):
        # If Grader 1 sends a new valid transaction object and then Grader 2 requests the same object,
        # Grader 2 should receive the object.
        client = await Client.new_established()
        await client.write(b'{"type":"object","object":{"height":1,"outputs":['
                           b'{"pubkey":"62b7c521cd9211579cf70fd4099315643767b96711febaa5c76dc3daf27c281c",'
                           b'"value":50000000000000}],"type":"transaction"}}\n')

        await client.write(b'{"type":"object","object":{"inputs":['
                           b'{"outpoint":{"index":0,"txid":"48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d0'
                           b'5c53802b69c7cd9fb"},"sig":"d51e82d5c121c5db21c83404aaa3f591f2099bccf731208c4b0b'
                           b'676308be1f994882f9d991c0ebfd8fdecc90a4aec6165fc3440ade9c83b043cba95b2bba1d0a"}],'
                           b'"outputs":[{"pubkey":"228ee807767047682e9a556ad1ed78dff8d7edf4bc2a5f4fa02e4634cfcad7e0",'
                           b'"value":49000000000000}],"type":"transaction"}}\n')

        client2 = await Client.new_established()
        await client2.write(
            b'{"type":"getobject","objectid":"d33ac384ea704025a6cac53f669c8e924eff7205b0cd0d6a231f0881b6265a8e"}\n')
        response = await client2.readline()
        self.assertIn(
            b'"48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d05c53802b69c7cd9fb"', response)
        self.assertIn(b'"type":"object"', response)
        await client.close()
        await client2.close()

    async def test_getIHaveObjMessage(self):
        # If Grader 1 sends a new valid transaction object, Grader 2 must receive an ihaveobject message with the
        # object id.
        client = await Client.new_established()
        client2 = await Client.new_established()

        await client.write(b'{"type":"object","object":{"height":1,"outputs":['
                           b'{"pubkey":"62b7c521cd9211579cf70fd4099315643767b96711febaa5c76dc3daf27c281c",'
                           b'"value":50000000000000}],"type":"transaction"}}\n')

        response = await client2.readline()
        self.assertIn(
            b'"objectid":"48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d05c53802b69c7cd9fb"', response)
        self.assertIn(b'"type":"ihaveobject"', response)
        await client.close()
        await client2.close()

    async def test_getGetObjMessage(self):
        # If Grader 1 sends an ihaveobject message with the id of a new object, Grader 1 must receive a getobject
        # message with the same object id.
        client = await Client.new_established()
        await client.write(
            b'{"type":"ihaveobject","objectid":"3e8174073cb429906c1a04d739b309f435d9333eed3f2904aa4d6ff10d01277b"}\n')
        response = await client.readline()
        self.assertIn(
            b'"objectid":"3e8174073cb429906c1a04d739b309f435d9333eed3f2904aa4d6ff10d01277b"', response)
        self.assertIn(b'"type":"getobject"', response)
        await client.close()

    async def test_objectSentAndHandshakeNotCompleted_shouldNotReceiveIHaveObject(self):
        client = await Client.new_established()
        client2 = await Client.new()
        await client2.readline()
        await client2.readline()
        await client2.readline()
        await client2.readline()

        await client.write(b'{"type":"object","object":{"type":"block","txids":['
                           b'"740bcfb434c89abe57bb2bc80290cd5495e87ebf8cd0dadb076bc50453590104"],'
                           b'"nonce":"a26d92800cf58e88a5ecf37156c031a4147c2128beeaf1cca2785c93242a4c8b",'
                           b'"previd":"0024839ec9632d382486ba7aac7e0bda3b4bda1d4bd79be9ae78e7e1e813ddd8",'
                           b'"created":1624219079,'
                           b'"T":"003a000000000000000000000000000000000000000000000000000000000000"}}\n')

        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(client2.readline(), 0.5)
        await client.close()
        await client2.close()
