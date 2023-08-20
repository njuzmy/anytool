import requests
import os
import pandas as pd
import datetime
import numpy as np
import ast
from ripe.atlas.cousteau import (
    Ping,
    Traceroute,
    AtlasSource,
    AtlasCreateRequest
)
from geopy.distance import great_circle
import threading
import time
import sys


class Measurement:
    def __init__(self, target=[], prb_lst=[], key_lst=[]):
        self.key_lst = key_lst
        self.target = target
        self.prb_lst = prb_lst
        self.mtr_mid = []

    def get_probe(self):
        def findStableTag(x):  # stable probe with tag "system-ipv4-stable-1d"
            for tag in x:
                for index, item in tag.items():
                    if item == "system-ipv4-stable-1d":
                        return True
            return False

        valid_probes = []
        current_page = "https://atlas.ripe.net:443/api/v2/probes/?status=1"

        while True:
            page = requests.get(current_page)
            if page.json()['next'] is not None:
                current_page = page.json()['next']
            else:
                break
            valid_probes += page.json()['results']  # get all valid probe

        self.valid_probe_pd = pd.DataFrame(valid_probes)
        self.valid_probe_pd["stable"] = self.valid_probe_pd['tags'].apply(lambda x: findStableTag(x))  # find all stable probe
        self.valid_probe_pd["location"] = self.valid_probe_pd["geometry"].str['coordinates']
        # sprobe_lst = self.valid_probe_pd[self.valid_probe_pd['stable']==True]['id'].to_list()

        filename = datetime.date.today().strftime("%Y-%m-%d")
        self.valid_probe_pd.to_csv(f"../dataset/srprobe_lst/{filename}")
        return
        # with open(f"../dataset/srprobe_lst/{filename}", "w+") as f:
        #     f.write(" ".join(map(str,sprobe_lst)))
        # return

    def traceroute(self, ip, pre_list, api_key):  # using ripe atlas to traceroute
        traceroute = Traceroute(
            af=4,
            target=ip,
            description=f"traceroute to {ip}",
            protocol="ICMP",
            resolve_on_probe=True
        )

        source3 = AtlasSource(
            type="probes",
            value=pre_list,
            requested=len(pre_list)
        )

        atlas_request = AtlasCreateRequest(
            key=api_key,
            measurements=[traceroute],
            sources=[source3],
            is_oneoff=True,
            resolve_on_probe=True
        )

        (is_success, response) = atlas_request.create()

        if is_success:
            return response['measurements'][0]
        else:
            print(response)
            return 'fail'

    def ping(self, ip, pre_list, api_key):

        ping = Ping(
            af=4,
            target=ip,
            description=f"ping to {ip}",
            protocol="ICMP",
            resolve_on_probe=True
        )

        source3 = AtlasSource(
            type="probes",
            value=pre_list,
            requested=len(pre_list)
        )

        atlas_request = AtlasCreateRequest(
            key=api_key,
            measurements=[ping],
            sources=[source3],
            is_oneoff=True
        )
        (is_success, response) = atlas_request.create()
        if is_success:
            return response['measurements'][0]  # return msm
        else:
            print(response)
            return 'fail'

    def measurement(self, fn):
        if len(self.key_lst) == 0:
            print("\033[1;31mplease provide your RIPE Atlas keys\033[0m")
            return
        if len(self.prb_lst) != 0:
            num = len(self.prb_lst) / 1000
            probe_lst = np.array_split(self.prb_lst, num + 1)
            files = os.listdir("../dataset/srprobe_lst/")
            filename = sorted(files, reverse=True)[0]                      # get the latest rsprobe_lst, get valid_probe_pd
            self.valid_probe_pd = pd.read_csv(f"../dataset/srprobe_lst/{filename}", index_col=0)
            self.valid_probe_pd['location'] = self.valid_probe_pd['location'].apply(lambda x: ast.literal_eval(x))
        else:
            self.get_probe()
            print("get probes done, running measurement")
            srprobe_lst = self.valid_probe_pd[self.valid_probe_pd['stable'] == True]['id'].to_list()
            num = len(srprobe_lst) / 1000
            probe_lst = np.array_split(srprobe_lst, num + 1)  # make sure number of probes of each splited list is less than 1000

        self.mtr_mid = []
        i = 0
        for ip in self.target:
            for split_probe in probe_lst:
                mid = "fail"
                while mid == "fail" and i < len(self.key_lst):
                    mid = fn(ip, ",".join([str(x) for x in split_probe]), self.key_lst[i])
                    i = i + 1
                if mid != "fail":
                    self.mtr_mid.append(mid)
                else:
                    print(f"\033[1;31mmeasurement fail, your finished measurement id is {self.mtr_mid}\033[0m")
                    return
        print("\033[1;32mmeasurement done!\033[0m")
        # if len(mtr_mid) == 0:
        #     with open(f"../dataset/measurement_id/{filename}", "w+") as f:
        #         f.write(" ".join(map(str,sprobe_lst)))
        #     return sprobe_lst
        return self.mtr_mid

    def getmtrid(self, mtr_lst=[]):  # assign the measurement_id instead of running a new round measurement
        files = os.listdir("../dataset/srprobe_lst/")
        filename = sorted(files, reverse=True)[0]                      # get the latest rsprobe_lst, get valid_probe_pd
        self.valid_probe_pd = pd.read_csv(f"../dataset/srprobe_lst/{filename}", index_col=0)
        self.valid_probe_pd['location'] = self.valid_probe_pd['location'].apply(lambda x: ast.literal_eval(x))
        self.mtr_mid = mtr_lst

    def tr_result(self):
        def ProcessTrace(in_result):
            ret_lst = []
            if 'error' in in_result[0]:
                # print ("Error")
                return None
            for each in in_result:
                current_hop = {}
                current_hop['hop'] = each['hop']
                ip_lst = []
                rtt_lst = []
                for each_ip in each['result']:
                    if "x" in each_ip:
                        continue
                    elif "from" in each_ip and "rtt" in each_ip:
                        ip_lst.append(each_ip['from'])
                        rtt_lst.append(each_ip['rtt'])
                    else:
                        continue
                if len(ip_lst) == 0:
                    current_hop['ip'] = "*"
                    current_hop['rtt'] = -1
                else:
                    current_hop['ip'] = ip_lst[0]
                    current_hop['rtt'] = min(rtt_lst)
                ret_lst.append(current_hop)
                ret_list = []
                is_push = False
                for each in ret_lst[::-1]:
                    if is_push == True:
                        ret_list.append(each)
                        continue
                    if each['ip'] == "*":
                        continue
                    else:
                        ret_list.append(each)
                        is_push = True
            return ret_list[::-1]

        """
        preprocess the data and transform it into dataframe
        """
        if len(self.mtr_mid) == 0:
            # self.measurement()
            # if len(self.mtr_mid) == 0:
            #     return
            print("\033[1;31mPlease first run measurement!\033[0m")
            return
        measure_pd_lst = [0 for i in range(len(self.mtr_mid))]

        # 多线程
        lock = threading.Lock()

        def read_measurement_json(i):
            ans = pd.read_json("https://atlas.ripe.net/api/v2/measurements/%s/results/?format=json&filename=RIPE-Atlas-measurement-%s.json" % (self.mtr_mid[i], self.mtr_mid[i]))
            with lock:
                measure_pd_lst[i] = ans

        threads = []
        for i in range(len(self.mtr_mid)):
            thread = threading.Thread(target=read_measurement_json, args=(i,))
            threads.append(thread)
            thread.start()

        while True:
            time.sleep(0.2)
            done_counter = 0
            for i in range(len(self.mtr_mid)):
                if isinstance(measure_pd_lst[i], pd.DataFrame):
                    done_counter += 1
            exit_counter = 0
            for thread in threads:
                if not thread.is_alive(): 
                    exit_counter += 1
            print("\r", end="")
            print("%-15s"%("Get results"),"progress: %5.1f%%: "%(done_counter/len(self.mtr_mid)*100), "▋" * (done_counter * 50 // len(self.mtr_mid)), end="")
            sys.stdout.flush()
            #print(f"\r{done_counter}/{len(self.mtr_mid)}", end="")

            if exit_counter == len(self.mtr_mid):
                if done_counter != exit_counter:
                    raise Exception("retriving error")
                break
        # print()
        # 结束


        # # for i in range(len(self.mtr_mid)):
        #     measure_pd_lst.append(pd.read_json("https://atlas.ripe.net/api/v2/measurements/%s/results/?format=json&filename=RIPE-Atlas-measurement-%s.json" % (self.mtr_mid[i], self.mtr_mid[i])))
        self.measure_pd = pd.concat(measure_pd_lst).reset_index()
        self.measure_pd['reduce_hop'] = self.measure_pd.apply(lambda x: ProcessTrace(x['result']), axis=1)
        self.measure_pd['p_hop'] = self.measure_pd['reduce_hop'].str[-2].str['ip']
        self.measure_pd['rtt'] = self.measure_pd['reduce_hop'].str[-1].str['rtt']
        self.measure_pd['p_rtt'] = self.measure_pd['reduce_hop'].str[-2].str['rtt']
        self.measure_pd = self.measure_pd[(~pd.isna(self.measure_pd['reduce_hop'])) & (self.measure_pd['reduce_hop'].str[-1].str['ip'].isin(self.target))]

    def ping_result(self):
        measure_pd_lst = []
        for i in range(len(self.mtr_mid)):
            measure_pd_lst.append(pd.read_json("https://atlas.ripe.net/api/v2/measurements/%s/results/?format=json&filename=RIPE-Atlas-measurement-%s.json" % (self.mtr_mid[i], self.mtr_mid[i])))
        self.measure_pd = pd.concat(measure_pd_lst).reset_index()
