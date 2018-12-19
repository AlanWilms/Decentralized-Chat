import etcd3

client = etcd3.client()

for k in client.get_all():
    print(k)

client.add_member("http://172.31.91.28:2380")
