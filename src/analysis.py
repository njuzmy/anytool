import threading
import time
import pandas as pd
import socket
import geoip2.database
import requests
import measurement
import subprocess
import ast
import sys
from tqdm import tqdm
from IPy import IP
from geopy.distance import great_circle
from geopy.geocoders import Nominatim


geolocator = Nominatim(user_agent="xxx")
known_dc = ["ali", "imperva", "edgio", "cloudflare", "akamai"]
geo_reader = geoip2.database.Reader("../dataset/geoip2/GeoLite2-City.mmdb")


class analysis:
    def __init__(self, key_lst=[], target=[], dc_name="", dc_file="", mtr_lst=[]):    # specify the CDN sites using name or file
        if dc_name != "":
            if dc_name not in known_dc:
                print(f"{dc_name}: dc not found")
            else:
                with open(f"../dataset/dc_lst/{dc_name}.txt") as f:
                    content = f.read()
                    self.dc_lst = eval(content)  # file should include site location with dict type
        elif dc_file != "":
            try:
                with open(f"{dc_file}") as f:
                    content = f.read()
                    self.dc_lst = eval(content)
            except BaseException:
                print("No such file.")
        else:
            print("Please specify the CDN you want to measure")
            raise
        self.measure = measurement.Measurement(target=target, key_lst=key_lst)
        if len(mtr_lst) != 0:
            print("retriving the results according to provided measurement ID")
            self.measure.getmtrid(mtr_lst)
        else:
            print("initializing the measurement")
            self.measure.measurement(self.measure.traceroute)

        self.measure.tr_result()                # get measurement's result pd
        self.mapping_dc_lst = []             # how many dc are mapped with phop
        self.repr_phop = {}                  # which phop can represent the site
        self.key_lst = key_lst               # store the key_lst
        print("done")

    def geolocate(self):  # geolocate the pen-hop
        def hoiho(rdns):
            result = requests.get(f"https://api.hoiho.caida.org/lookups/{rdns}")  # extract geolocation from hostname
            try:
                result = eval(result.text)
                if "matches" in result.keys():
                    loc = f"{result['matches']['place']}|{result['matches']['lat']},{result['matches']['lon']}"
                    return loc
                return None
            except BaseException:
                # print(f"something wrong when using hoiho:{result}")
                return None

        def extracerDNS(ip):
            try:
                rdns = socket.gethostbyaddr(ip)[0]
                return hoiho(rdns)
            except BaseException:
                return None

        def ipinfo(ip):
            # TODO
            try:
                loc = requests.get("https://ipinfo.io/%s/json?token=2c732d429c11a8" % ip).json()
            except BaseException:
                loc = ""
            if "country" in loc:
                return f"{loc['country']}|{loc['city']}|{loc['loc']}"
            else:
                return None

        def maxmind(ip):
            try:
                response = geo_reader.city(ip)
                return response.country.name + "|" + response.city.name + "|" + response.location.latitude.__str__() + ',' + response.location.longitude.__str__()
            except BaseException:
                return None

        def nearestPrb(phop):
            try:
                prb_pd = self.measure.measure_pd[self.measure.measure_pd['p_hop'] == phop].sort_values('p_rtt')
                i = 0
                loc = []
                while (i < len(prb_pd) and len(loc) == 0):
                    cur_prb = self.measure.measure_pd[self.measure.measure_pd['p_hop'] == phop].sort_values('p_rtt').iloc[i]
                    loc = self.measure.valid_probe_pd[self.measure.valid_probe_pd['id'] == cur_prb["prb_id"]]['location'].to_list()
                    i += 1
                if len(loc) > 0:
                    return (loc[0][::-1], cur_prb['p_rtt'])
                else:
                    return None
            except BaseException:
                return None

        def extractDist(data):
            try:
                geos = [data["rdns-geo"], data["ipinfo-geo"], data["maxmind-geo"]]
                if data['nearest_prb_loc'] is not None:
                    lat, lon = data['nearest_prb_loc'][0][0], data['nearest_prb_loc'][0][1]
                    dist = []
                    for each in geos:
                        if each is not None:
                            cur_lat, cur_lon = each.split("|")[-1].split(",")
                            dist.append((great_circle((cur_lat, cur_lon), (lat, lon)).km, each))
                    if len(dist) == 0:
                        if data['nearest_prb_loc'][1] < 1:
                            return geolocator.reverse(f"{lat} {lon}").address + '|' + str(lat) + ',' + str(lon)  # return closest probe's location
                        else:
                            return None
                    opt_choice = sorted(dist)[0]
                    if opt_choice[0] < 600 and data['nearest_prb_loc'][1] < 6:  # if the distance to the nearest probe is less than 600 km and the rtt to the phop is less than 6 ms
                        return opt_choice[1]
                    else:
                        return None
                else:
                    return data["ipinfo-geo"]
            except BaseException:
                return None

        def parallel(fn, col, info_source):
            #print(col)
            lock = threading.Lock()

            ans_dict = {}

            def multi_thread(fn, index, row):
                data = [index, row][info_source]
                ans = fn(data)
                with lock:
                    ans_dict[index] = ans

            threads = []

            for index, row in self.phop_pd.iterrows():
                thread = threading.Thread(target=multi_thread, args=(fn, index, row,))
                threads.append(thread)
                thread.start()

            while True:
                time.sleep(0.2)
                done_counter = len(ans_dict)
                exit_counter = 0
                for thread in threads:
                    if not thread.is_alive():
                        exit_counter += 1
                print("\r", end="")
                print("%-15s"%col, "progress: %5.1f%%: "%(done_counter / self.phop_pd.shape[0] * 100), "▋" * (done_counter * 50 // self.phop_pd.shape[0]), end="")
                sys.stdout.flush()
                # print(f"\r{done_counter}/{self.phop_pd.shape[0]}", end="")

                if exit_counter == self.phop_pd.shape[0]:
                    if done_counter != exit_counter:
                        raise Exception(f"something error when {col}")
                    break
            print()

            # self.phop_pd[col] = pd.Series()
            # print(ans_dict)
            # # self.phop_pd[col] = self.phop_pd[col].astype(object)
            # for k, v in ans_dict.items():
            #     self.phop_pd.at[k, col] = v
            self.phop_pd = self.phop_pd.merge(pd.DataFrame([ans_dict]).T.rename(columns={0:col}),left_index=True,right_index=True)

        try:
            print("geolocating the phop...")
            self.phop_pd = pd.DataFrame(self.measure.measure_pd['p_hop'].value_counts())
            self.phop_pd = self.phop_pd[self.phop_pd.index != '*']

            parallel(extracerDNS, "rdns-geo", 0)
            parallel(ipinfo, "ipinfo-geo", 0)
            parallel(maxmind, "maxmind-geo", 0)
            parallel(nearestPrb, "nearest_prb_loc", 0)
            parallel(extractDist, "location", 1)

            # self.phop_pd['rdns-geo'] = self.phop_pd.apply(lambda x: extracerDNS(x.name), axis=1)
            # self.phop_pd['ipinfo-geo'] = self.phop_pd.apply(lambda x: ipinfo(x.name), axis=1)
            # self.phop_pd['maxmind-geo'] = self.phop_pd.apply(lambda x: maxmind(x.name), axis=1)
            # self.phop_pd['nearest_prb_loc'] = self.phop_pd.apply(lambda x: nearestPrb(x.name), axis=1)
            # self.phop_pd['location'] = self.phop_pd.apply(lambda x: extractDist(x), axis=1)

            self.phop_pd = self.phop_pd[~pd.isna(self.phop_pd["location"])]
            #print(self.phop_pd)
        except Exception as e:
            print(e)
            print("something error when geolocating phop_pd")

    def mapsite(self):
        def DC_tracer(geo):
            if geo is not None:
                curlat, curlon = geo.split('|')[-1].split(',')
                curlat, curlon = float(curlat), float(curlon)
                dist = []
                for each in self.dc_lst:  # dc:"lat,lon"
                    for city, item in each.items():
                        dclat, dclon = item.split(",")
                        dclat, dclon = float(dclat), float(dclon)
                        dist.append((great_circle((curlat, curlon), (dclat, dclon)).km, f"{city}|{item}"))
                return sorted(dist)[0][1]  # phop mapped to dc(city|geo)
            else:
                return None

        try:
            self.geolocate()
            print("mapping phop to the site ...")
            self.phop_pd['mapped_site'] = self.phop_pd['location'].apply(lambda x: DC_tracer(x))
            self.mapping_dc_lst = self.phop_pd['mapped_site'].value_counts().index.to_list()  # mapped site
            print(f"In total, using RIPE Atlas can resolve {len(self.mapping_dc_lst)} sites with {len(self.dc_lst)-len(self.mapping_dc_lst)} sites left unresolvable.")
        except Exception as e:
            print(e)
            print("something error when mapping sites")

    def reprePhop(self):  # we want to know which phop is close enough to be unicast representatives
        def check_ip_ping(ip):
            p = subprocess.Popen(['bash', 'ping.sh', ip], stdout=subprocess.PIPE)
            result = p.stdout.read()
            if result == b'1\n':
                return False
            else:
                return True

        def bogonip(ip):
            bogon_ip_range = ["0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "127.0.53.53", "169.254.0.0/16", "172.16.0.0/12", "192.0.0.0/24",
                              "192.0.2.0/24", "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24", "224.0.0.0/4", "240.0.0.0/4", "255.255.255.255/32"]
            for ran in bogon_ip_range:
                if ip in IP(ran):
                    return True
            return False

        self.repr_phop = {}
        i = 0
        lock = threading.Lock()

        def my_fn(phop):
            if phop['location'] is not None:
                phop_lat, phop_lon = phop['location'].split('|')[-1].split(',')
                site_lat, site_lon = phop['mapped_site'].split('|')[-1].split(',')
                mapped_site = phop['mapped_site'].split('|')[0]

                with lock:
                    keys = self.repr_phop

                if mapped_site not in keys:
                    if great_circle((phop_lat, phop_lon), (site_lat, site_lon)).km < 600 and check_ip_ping(phop.name) and not bogonip(phop.name):
                        ans = [phop.name, great_circle((phop_lat, phop_lon), (site_lat, site_lon)).km]
                        with lock:
                            self.repr_phop[mapped_site] = ans

                else:
                    if great_circle((phop_lat, phop_lon), (site_lat, site_lon)).km < self.repr_phop[mapped_site][1] and check_ip_ping(phop.name) and not bogonip(phop.name):
                        ans = [phop.name, great_circle((phop_lat, phop_lon), (site_lat, site_lon)).km]
                        with lock:
                            self.repr_phop[mapped_site] = ans
        threads = []

        for index, row in self.phop_pd.iterrows():
            thread = threading.Thread(target=my_fn, args=(row,))
            threads.append(thread)
            thread.start()

        while True:
            time.sleep(0.2)
            exit_counter = 0
            for thread in threads:
                if not thread.is_alive():
                    exit_counter += 1
            print("\r", end="")
            print("Get the results: {:.1f}%: ".format(exit_counter / self.phop_pd.shape[0] * 100), "▋" * (exit_counter * 50 // self.phop_pd.shape[0]), end="")
            sys.stdout.flush()
            # print(f"\r{exit_counter}/{self.phop_pd.shape[0]}", end="")

            if exit_counter == self.phop_pd.shape[0]:
                break
        print()

        # for _, phop in self.phop_pd.iterrows():
        #     print(i)
        #     i+=1
        #     if phop['location'] is not None:
        #         phop_lat, phop_lon = phop['location'].split('|')[-1].split(',')
        #         site_lat, site_lon = phop['mapped_site'].split('|')[-1].split(',')
        #         mapped_site = phop['mapped_site'].split('|')[0]
        #         if mapped_site not in self.repr_phop:
        #             if great_circle((phop_lat, phop_lon), (site_lat, site_lon)).km < 600 and check_ip_ping(phop.name) and not bogonip(phop.name):
        #                 self.repr_phop[mapped_site] = [phop.name, great_circle((phop_lat, phop_lon), (site_lat, site_lon)).km]
        #         else:
        #             if great_circle((phop_lat, phop_lon), (site_lat, site_lon)).km < self.repr_phop[mapped_site][1] and check_ip_ping(phop.name) and not bogonip(phop.name):
        #                 self.repr_phop[mapped_site] = [phop.name, great_circle((phop_lat, phop_lon), (site_lat, site_lon)).km]
        print(f"In total, we can find {len(self.repr_phop)} sites' unicast representitives.")

    def geoanalysis(self):          # we want to know how many probes are routed to the closest site geographically
        def siteRank(data):
            try:
                dis = great_circle((data["mapped_site"].split("|")[1].split(",")[0], data["mapped_site"].split("|")[1].split(",")[1]), (data['lat'], data['lon'])).km
                rank = 0
                for site in self.mapping_dc_lst:
                    if dis > great_circle((site.split("|")[1].split(",")[0], site.split("|")[1].split(",")[1]), (data['lat'], data['lon'])).km:
                        rank += 1
                return rank
            except BaseException:
                return None

        self.measure.measure_pd = self.measure.measure_pd.merge(self.phop_pd[["mapped_site"]], left_on="p_hop", right_index=True)
        self.measure.measure_pd = self.measure.measure_pd.merge(self.measure.valid_probe_pd[['id', 'location']], left_on="prb_id", right_on="id")
        self.measure.measure_pd['lat'] = self.measure.measure_pd['location'].str[1]
        self.measure.measure_pd['lon'] = self.measure.measure_pd['location'].str[0]
        self.measure.measure_pd['site_rank'] = self.measure.measure_pd.apply(lambda x: siteRank(x), axis=1)
        print(f"{round(len(self.measure.measure_pd[self.measure.measure_pd['site_rank']==0])/len(self.measure.measure_pd)*100,1)}% ({len(self.measure.measure_pd[self.measure.measure_pd['site_rank']==0])}/{len(self.measure.measure_pd)}) probes are routed to the closest site")
        # print(self.measure.measure_pd['site_rank'].value_counts().head(5))
        # print("...")
        # print(self.measure.measure_pd['site_rank'].value_counts.tail(5))

        "merge"
        # dist = [great_circle((x.split("|")[1].split(",")[0], x.split("|")[1].split(",")[1]), (data['lat'],data['lon'])).km for x in self.mapping_dc_lst]

    def rttanalysis(self, msm_file=""):          # we want to know how many probes are routed to the lowest-latency site
        def topthree(data):         # select three closest sites
            dis_dict = {}
            for site in self.mapping_dc_lst:
                dis_dict[site] = great_circle((site.split("|")[1].split(",")[0], site.split("|")[1].split(",")[1]), (data['lat'], data['lon'])).km
            dis_dict = sorted(dis_dict.items(), key=lambda x: x[1])
            return [x[0].split("|")[0] for x in dis_dict[0:3]]

        def sortRTT(data):
            if data['mapped_site'] is not None and data['mapped_site'].split("|")[0] in data['clsthree'] and data['mapped_site'].split(
                    "|")[0] in self.repr_phop.keys() and self.repr_phop[data['mapped_site'].split("|")[0]][0] in data.index:
                real_rtt = data[self.repr_phop[data['mapped_site'].split("|")[0]][0]]
                if real_rtt != -1 and str(real_rtt) != "nan":
                    rank = 0
                    for site in data['clsthree']:
                        if site in self.repr_phop.keys() and self.repr_phop[site][0] in data.index and data[self.repr_phop[site][0]] is not None:
                            if data[self.repr_phop[site][0]] < real_rtt:
                                rank += 1
                    return rank
                else:
                    return -1
            elif data['mapped_site'] is not None and data['mapped_site'].split("|")[0] not in data['clsthree']:                    # mapped sites is not in the closest three sites
                rank = 0
                for site in data['clsthree']:
                    if site in self.repr_phop.keys() and self.repr_phop[site][0] in data.index and data[self.repr_phop[site][0]] is not None:
                        if data[self.repr_phop[site][0]] < data['rtt']:
                            rank += 1
                return rank
            else:
                return -1

        measure_ins_lst = []
        measure_pd_lst = []
        self.measure.measure_pd["clsthree"] = self.measure.measure_pd.apply(lambda x: topthree(x), axis=1)

        def parallel(msm_id_lst):
            lock = threading.Lock()

            done_counter_ = []

            def multi_thread(id_lst):
                a = measurement.Measurement()
                a.getmtrid(id_lst)
                a.ping_result()
                target = a.measure_pd['dst_addr'].value_counts().index[0]
                a.measure_pd.rename(columns={"avg": target}, inplace=True)
                if "prb_id" in a.measure_pd.columns:                  # whether the measure_pd is null
                    a.measure_pd.set_index("prb_id", inplace=True)
                    with lock:
                        measure_pd_lst.append(a.measure_pd[[target]])
                        done_counter_.append(1)

            threads = []

            for id_lst in msm_id_lst:
                thread = threading.Thread(target=multi_thread, args=(id_lst,))
                threads.append(thread)
                thread.start()

            while True:
                time.sleep(0.2)
                exit_counter = 0
                done_counter = len(done_counter_)
                for thread in threads:
                    if not thread.is_alive():
                        exit_counter += 1
                print("\r", end="")
                print("Get the results: {:.1f}%: ".format(done_counter / len(msm_id_lst) * 100), "▋" * (done_counter * 50 // len(msm_id_lst)), end="")
                sys.stdout.flush()
                # print(f"\r{done_counter}/{len(msm_id_lst)}", end="")

                if exit_counter == len(msm_id_lst):
                    if done_counter != exit_counter:
                        raise Exception(f"something error")
                    break
            print()

        if msm_file == "":
            measure_dict = {}
            for _, item in self.measure.measure_pd.iterrows():
                for site in item["clsthree"]:
                    if site in self.repr_phop.keys():
                        if self.repr_phop[site][0] not in measure_dict.keys():
                            measure_dict[self.repr_phop[site][0]] = [item['prb_id']]
                        else:
                            measure_dict[self.repr_phop[site][0]].append(item['prb_id'])

            for target, prb_lst in measure_dict.items():
                a = measurement.Measurement(target=[target], key_lst=self.key_lst, prb_lst=prb_lst)
                measure_ins_lst.append(a)
                a.measurement(a.ping)
                a.ping_result()
                a.measure_pd.rename(columns={"avg": target}, inplace=True)
                if "prb_id" in a.measure_pd.columns:                  # whether the measure_pd is null
                    a.measure_pd.set_index("prb_id")
                    measure_pd_lst.append(a.measure_pd[[target]])
        else:
            with open(msm_file, 'r') as f:
                lines = f.read()
            msm_id_lst = ast.literal_eval(lines)
            parallel(msm_id_lst)

        self.rtt_pd = pd.concat(measure_pd_lst, axis=1, join="outer")
        self.rtt_pd = self.rtt_pd.merge(self.measure.measure_pd[['prb_id', 'mapped_site', 'clsthree', 'rtt']], left_index=True, right_on="prb_id")
        tqdm.pandas(desc="analyzing")
        self.rtt_pd['rtt_rank'] = self.rtt_pd.progress_apply(lambda x: sortRTT(x), axis=1)

        print(
            f"Of {len(self.measure.measure_pd)} probes, we sucessfully analyze {len(self.rtt_pd[self.rtt_pd['rtt_rank']!=-1])} probes' rtt performance. As a result, {round(len(self.rtt_pd[self.rtt_pd['rtt_rank']==0])/len(self.rtt_pd[self.rtt_pd['rtt_rank']!=-1])*100,1)}% ({len(self.rtt_pd[self.rtt_pd['rtt_rank']==0])}/{len(self.rtt_pd[self.rtt_pd['rtt_rank']!=-1])}) probes are routed to the lowest-latency site")
