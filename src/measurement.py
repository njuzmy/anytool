import requests
import os
import pandas as pd
import datetime
import numpy as np
from ripe.atlas.cousteau import (
  Ping,
  Dns,
  Probe,
  Traceroute,
  AtlasSource,
  AtlasCreateRequest,
  AtlasResultsRequest
)
from geopy.distance import great_circle

class Measurement:
    def __init__(self, key_lst, target=[], ):
        self.key_lst = key_lst
        self.target = target
        self.mtr_mid = []


    def get_probe():
        def findStableTag(x): #stable probe with tag "system-ipv4-stable-1d"
            for tag in x:
                for index, item in tag.items():
                    if item == "system-ipv4-stable-1d":
                        return True
            return False

        valid_probes = []
        current_page = "https://atlas.ripe.net:443/api/v2/probes/?status=1"

        while True:
            page = requests.get(current_page)
            if page.json()['next'] != None:
                current_page = page.json()['next']
            else:
                break
            valid_probes += page.json()['results']           #get all valid probe

        valid_probe_pd = pd.DataFrame(valid_probes)
        valid_probe_pd["stable"] = valid_probe_pd['tags'].apply(lambda x: findStableTag(x))  #find all stable probe
        sprobe_lst = valid_probe_pd[valid_probe_pd['stable']==True]['id'].to_list()

        filename = datetime.date.today().strftime("%Y-%m-%d")
        with open(f"../dataset/srprobe_lst/{filename}", "w+") as f:
            f.write(" ".join(map(str,sprobe_lst)))
        return sprobe_lst

    def traceroute(self,ip,pre_list, num, api_key):      #using ripe atlas to traceroute
        traceroute = Traceroute(
            af=4,
            target=ip,
            description="traceroute to",
            protocol="ICMP",
            resolve_on_probe=True
        )

        source3 = AtlasSource(
            type="probes",
            value=pre_list,
            requested=num
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

    def measurement(self):
        files = os.listdir("../dataset/srprobe_lst/")
        filename = files.sort()[0]                      # get the latest rsprobe_lst
        with open(f"../dataset/srprobe_lst/{filename}") as f:
            content = f.read()
        srprobe = [int(x) for x in content.split()]

        probe_lst = np.array_split(srprobe_lst, 12)   #make sure number of probes of each splited list is less than 1000

        self.mtr_mid = []
        i = 0
        for ip in self.target:
            mid = "fail"
            for split_probe in probe_lst:
                while mid == "fail" and i < len(self.key_lst):
                    mid = traceroute(ip, ",".join([str(x) for x in split_probe]), len(split_probe), self.key_lst[i])
                    i = i + 1
                if mid != "fail":
                    self.mtr_mid.append(mid)
                else:
                    print("measurement fail")
        # if len(mtr_mid) == 0:
        #     with open(f"../dataset/measurement_id/{filename}", "w+") as f:
        #         f.write(" ".join(map(str,sprobe_lst)))
        #     return sprobe_lst
        return

    def analysis(self):
        def ProcessTrace(in_result):
            ret_lst = []
            if 'error' in in_result[0]:
                #print ("Error")
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
        measure_pd_lst = []
        for i in range(self.mtr_mid):
            measure_pd_lst.append(pd.read_json("https://atlas.ripe.net/api/v2/measurements/%s/results/?format=json&filename=RIPE-Atlas-measurement-%s.json" % (self.mtr_mid[i], self.mtr_mid[i])))
        self.measure_pd = pd.concat(measure_pd_lst).reset_index()
        self.measure_pd['reduce_hop'] = self.measure_pd.apply(lambda x: ProcessTrace(x['result']), axis=1)
        self.measure_pd['p_hop'] = self.measure_pd['reduce_hop'].str[-2].str['ip']
        self.measure_pd = self.measure_pd[(~pd.isna(self.measure_pd['reduce_hop'])) & (self.measure_pd['reduce_hop'].str[-1].str['ip'].isin(self.target))]

