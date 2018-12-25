# coding=utf-8
# dongfang.yuan

import sys
reload(sys)
sys.path.append('./')
sys.path.append('../')
sys.setdefaultencoding('utf-8')

import os
import time
import json
import zlib
import random
# import urllib2

from multiprocessing import Process
from interface.gen_api import price_service_pb2 
from lib.google.protobuf import text_format
from utils import mmhash 
from gevent import monkey; monkey.patch_all()
import gevent
import urllib2
from datetime import datetime

HIDS = {
    '13': [288157],
    '14': [165930],
}

def build_req(oid, bids=[], req_type=2):
    oa_request = price_service_pb2.OaRequest()
    oa_request.ota_id = int(oid)
    oa_request.request_type = int(req_type)
    #oa_request.non_limit = True
    oa_request.search_id = str(mmhash.get_hash(str(time.time())))
    oa_request.user_info.booking_channel = 2 
    # oa_request.user_info.booking_channel = 16 
    # oa_request.user_info.booking_channel = 64 
    if len(bids) == 0:
        try:
            bids = HIDS[oid]
        except:
            bids = [324748]
    query_info = oa_request.query_info
    for bid in bids:
        query_info.hotel_id.append(int(bid))

    query_info.check_in_date = int(time.mktime(time.strptime("2018-12-27", "%Y-%m-%d")))
    query_info.check_out_date = int(time.mktime(time.strptime("2018-12-29", "%Y-%m-%d"))) 
    person = query_info.room_person.add()
    person.adult_num = 2 
    # person.child_age_list.append(7)

    # print oa_request.__unicode__()
    ret = oa_request.SerializeToString()
    return oa_request.SerializeToString()
    
def fetch_test(oid, bid, res_file, ip='0.0.0.0', index=0):
    ret_info = {
        'index': index,
        'ip': ip,
        'hotel_info': {'oid': oid, 'bid': bid},
        'req_time': -1,
        'resp_time': -1,
        'resp_code': -1,
        'resp_info': -1,
        'oa_resp': '',
        'error_info': ''
    }
    url = "http://%s:8300?&update=0" % ip 
    rqs = build_req(oid, bid)
    request = urllib2.Request(url, data=rqs)
    request.add_header("User-Agent", "chrome") 
    try:
        time1= time.time() * 1000 
        f = urllib2.urlopen(request)
        page = f.read()
        ret = price_service_pb2.OaResponse() 
        ret.ParseFromString(page)
        ret_info['resp_code'] = f.code
        ret_info['resp_info'] = str(f.info())
    except Exception as e:
        print e
        ret_info['error_info'] = str(e)
    else:
        ret_info['oa_resp'] = {
            'subcode':ret.service_status.sub_code,
            'msg': ret.service_status.msg
            }
        ret_info['search_id'] = ret.search_id,
    finally:
        time3= time.time() * 1000
        ret_info['req_time'] = int(time1)
        ret_info['resp_time'] = int(time3)
        ret_info['total_time'] = int(time3 - time1)
    
    res_file.write(json.dumps(ret_info))
    res_file.write('\n')

    return ret_info


# process
def pressure_process(hotel_info_list, time_length=20, pindex=0, coroutine_num=10, file_prefix=None):
    if not pindex:
        pindex = os.getpid()
    if not file_prefix:
        res_file_name = '%s_statistics_%s' % (datetime.now().strftime("%Y%m%d%H%M%S"), pindex)
    else:
        res_file_name = '%s_statistics_%s' % (file_prefix, pindex)
    
    if not os.path.isdir('pressure_logs'):
        os.mkdir('pressure_logs')
    res_file = open(os.path.join('pressure_logs', res_file_name), 'w')

    start_time = time.time()
    count = 0
    while True:
        if time.time() - start_time > time_length:
            break
        
        coroutines = []
        for _ in range(coroutine_num):
            (oid, bid) = random.choice(hotel_info_list)
            coroutines.append(gevent.spawn(fetch_test, oid, [bid], res_file, '0.0.0.0', count))
            count += 1

        gevent.joinall(coroutines)
    
    res_file.close()

def pressure_main_test(process_num=5, target_ip=['0.0.0.0', ]):
    file_prefix = datetime.now().strftime("%Y%m%d%H%M%S")
    print file_prefix
    hotel_info_list = []
    with open('param_ret') as f:
        for line in f:
            hotel_info_list.append(tuple(line.strip().split('_')))
    pro_list = []
    for i in range(process_num):
        pro = Process(target=pressure_process, args=(hotel_info_list, 30, i+1, 100, file_prefix))
        pro_list.append(pro)
        pro.start()
    
    for p in pro_list:
        p.join()



def record_param():
    pass


def extract_pressure_log(line_info):
    line_info = json.loads(line_info.strip())
    return {
        'end_time': line_info['resp_time'],
        'rt': line_info['total_time'],
        'start_time': line_info['req_time'],
    }

# parse line to generate qps info
def extract_in_out(line_info):
    line_info = json.loads(line_info.strip())
    return {
        'end_time': line_info['logTime'],
        'rt': line_info['useTime'],
        'start_time': line_info['logTime'] - line_info['useTime']
    }
    
def cal_qps_info(file_full_path, extract_func):
    # src_info_format = {
    #     'start_time': -1,
    #     'end_time': -1,
    #     'rt' -1
    # }
    
    # attention to time unit is millisecond
    qps_info = {
        'query_count': 0,
        'rt_avg': -1,
        'rt_max': -1,
        'rt_min': 10000000,
        'query_time_section': -1,
        'query_start_time': time.time() * 1000,
        'query_end_time': -1,
        'error_count': 0
    }

    query_start_time = int(time.time() * 1000)
    query_end_time = 0
    rt_total = 0.0
    with open(file_full_path) as f:
        for line in f:
            qps_info['query_count'] += 1
            try:
                extract_info = extract_func(line.strip('\n'))
            except:
                qps_info['error_count'] += 1
                continue

            rt_total += extract_info['rt']
            qps_info['rt_max'] = extract_info['rt'] if \
                extract_info['rt'] > qps_info['rt_max'] else qps_info['rt_max']

            qps_info['rt_min'] = extract_info['rt'] if \
                extract_info['rt'] < qps_info['rt_min'] else qps_info['rt_min']

            query_start_time = extract_info['start_time'] \
                if extract_info['start_time'] < query_start_time else query_start_time
            
            query_end_time = extract_info['end_time'] \
                if extract_info['end_time'] > query_end_time else query_end_time

    qps_info['query_time_section'] = query_end_time - query_start_time
    qps_info['query_start_time'] = query_start_time
    qps_info['query_end_time'] = query_end_time
    qps_info['rt_avg'] = rt_total / (qps_info['query_count'] - qps_info['error_count'])

    qps = qps_info['query_count'] * 1000.0 / qps_info['query_time_section']
    print json.dumps(qps_info, indent=4)
    return qps


def cal_oa_log_qps():
    file_path = 'in_out'
    file_name = 'in_out.log.1'
    file_full_path = os.path.join(file_path, file_name)
    print cal_qps_info(file_full_path, extract_in_out)


def cal_oa_pressure_qps():
    file_path = '/pressure_logs'
    file_name = '20181225031946_statistics_5'
    file_full_path = os.path.join(file_path, file_name)
    print cal_qps_info(file_full_path, extract_pressure_log)


def main():
    # cal_oa_log_qps()
    cal_oa_pressure_qps()
    # pressure_main_test()

        
if __name__ == '__main__':
    main()