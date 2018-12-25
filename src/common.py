# coding: utf-8
# dongfang.yuan


ip_list = [
    "172.18.118.179",
    "172.18.118.186",
    "172.18.118.187",
    "172.18.118.188",
    "172.18.118.190",
    "172.18.118.191",
    "172.18.118.192",
    "172.18.118.193",
    "172.18.118.189",
    "172.18.118.212",
    "172.18.118.213",
    "172.18.118.214",
    "172.18.118.215",
    "172.18.118.216",
    "172.18.118.217",
    "172.18.118.218",
    "172.18.118.219",
    "172.18.118.220",
    "172.18.118.221",
    "172.18.118.222",
    "172.18.118.223",
    "172.18.118.224",
    "172.18.118.225",
    "172.18.118.226",
    "172.18.118.227",
]


def get_idMap():
    filename = '/home/work/ilog/oa/in_out/in_out.log.1'
    tar_file =  open('param', 'w')

    with open(filename) as f:
        for line in f:
            log_item = json.loads(line.strip())
            idmap = log_item.get('idMap')
            tar_file.write(json.dumps(idmap))
            tar_file.write('\n')

    tar_file.close()


def parse_idMap(filename='param'):
    ret_id = set()
    with open(filename) as f:
        for line in f:
            idmap = json.loads(line.strip())
            ret_id.add("{}_{}".format(idmap['otaId'], idmap['hotelId']))

    with open('param_ret', 'w') as f:
        for _id in ret_id:
            f.write(_id)
            f.write('\n')
