import pandas as pd
import socket
import geoip2.database
import requests
import measurement
from geopy.distance import great_circle
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="xxx")
known_dc = ["ali", "imperva"]
geo_reader = geoip2.database.Reader("../dataset/geoip2/GeoLite2-City.mmdb")

class analysis:  
    def __init__(self, key_lst=[], target=[], dc_name="", dc_file="", mtr_lst=[]):    # specify the CDN sites using name or file
        if dc_name != "":
            if dc_name not in known_dc:
                print(f"{dc_name}: dc not found")
            else:
                with open(f"../dataset/dc_lst/{dc_name}.txt") as f:
                    content = f.read()
                    self.dc_lst = eval(content)   #file should include site location with dict type
        elif dc_file != "":
            try:
                with open(f"{dc_file}") as f:
                    content = f.read()
                    self.dc_lst = eval(content)
            except:
                print("No such file.")
        else:
            print("Please specify the CDN you want to measure")
            raise
        self.measure = measurement.Measurement(key_lst, target)
        if len(mtr_lst) != 0:
            self.measure.getmtrid(mtr_lst)
        self.measure.result()                # get result pd
        self.mapping_dc_lst = []             # how many dc are mapped with phop
        self.repr_phop = {}                  # which phop can represent the site
        

    def geolocate(self):     #geolocate the pen-hop 
        def hoiho(rdns):
            result = requests.get(f"https://api.hoiho.caida.org/lookups/{rdns}")    #extract geolocation from hostname
            try:
                result = eval(result.text)
                if "matches" in result.keys():
                    loc = f"{result['matches']['place']}|{result['matches']['lat']},{result['matches']['lon']}"
                    return loc
                return None
            except:
                #print(f"something wrong when using hoiho:{result}")
                return None
            

        def extracerDNS(ip):
            try:
                rdns = socket.gethostbyaddr(ip)[0]
                return hoiho(rdns)
            except:
                return None
        
        def ipinfo(ip):
            loc = requests.get("https://ipinfo.io/%s/json?token=2c732d429c11a8"%ip).json()
            if "country" in loc:
                return f"{loc['country']}|{loc['city']}|{loc['loc']}"
            else:
                return None
            
        def maxmind(ip):
            try:
                response = geo_reader.city(ip)
                return response.country.name + "|" + response.city.name + "|" + response.location.latitude.__str__() +',' + response.location.longitude.__str__()
            except:
                return None
            
        def nearestPrb(phop):
            try:
                prb_pd = self.measure.measure_pd[self.measure.measure_pd['p_hop'] == phop].sort_values('p_rtt')
                i = 0
                loc = []
                while(i < len(prb_pd) and len(loc) == 0):
                    cur_prb = self.measure_pd[self.measure_pd['p_hop'] == phop].sort_values('p_rtt').iloc[i]
                    loc = self.valid_probe_pd[self.valid_probe_pd['id'] == cur_prb["prb_id"]]['location'].to_list()
                    i += 1
                if len(loc) > 0:
                    return (loc[0][::-1], cur_prb['p_rtt'])
                else:
                    return None
            except:
                return None
                        
        def extractDist(data):
            try:
                geos = [data["rdns-geo"], data["ipinfo-geo"], data["maxmind-geo"]]
                if data['nearest_prb_loc'] != None:
                    lat,lon = lat,lon = data['nearest_prb_loc'][0][0], data['nearest_prb_loc'][0][1]
                    dist = []
                    for each in geos:
                        if each != None:
                            cur_lat, cur_lon = each.split("|")[-1].split(",")
                            dist.append((great_circle((cur_lat,cur_lon),(lat,lon)).km, each))
                    if len(dist) == 0:
                        if data['nearest_prb_loc'][1] < 1:
                            return geolocator.reverse(f"{lat} {lon}").address + '|' + str(lat)+ ',' + str(lon)   #return closest probe's location
                        else:
                            return None
                    opt_choice = sorted(dist)[0]
                    if opt_choice[0] < 600 and data['nearest_prb_loc'][1] < 6:       #if the distance to the nearest probe is less than 600 km and the rtt to the phop is less than 6 ms
                        return opt_choice[1]
                    else:
                        return None
                else:
                    return data["ipinfo-geo"]
            except:
                return None
            
        try:
            print("geolocating the phop...")
            self.phop_pd = pd.DataFrame(self.measure.measure_pd['p_hop'].value_counts())
            self.phop_pd = self.phop_pd[self.phop_pd.index!='*']
            self.phop_pd['rdns-geo'] = self.phop_pd.apply(lambda x: extracerDNS(x.name), axis=1)
            self.phop_pd['ipinfo-geo'] = self.phop_pd.apply(lambda x: ipinfo(x.name), axis=1)
            self.phop_pd['maxmind-geo'] = self.phop_pd.apply(lambda x: maxmind(x.name), axis=1)
            self.phop_pd['nearest_prb_loc'] = self.phop_pd.apply(lambda x: nearestPrb(x.name), axis=1)    
            self.phop_pd['location'] = self.phop_pd.apply(lambda x: extractDist(x), axis=1)
            self.phop_pd = self.phop_pd[~pd.isna(self.phop_pd["location"])]
        except Exception as e:
            print(e)
            print("something error when geolocating phop_pd")

    def mapsite(self): 
        def DC_tracer(geo):
            if geo != None:
                curlat, curlon = geo.split('|')[-1].split(',')
                curlat, curlon = float(curlat), float(curlon)
                dist = []
                for each in self.dc_lst:   #dc:"lat,lon"
                    for city, item in each.items():
                        dclat, dclon = item.split(",")
                        dclat, dclon = float(dclat), float(dclon)
                        dist.append((great_circle((curlat,curlon),(dclat,dclon)).km, f"{city}|{item}"))     
                return sorted(dist)[0][1]                             #phop mapped to dc(city|geo)
            else:
                return None

        try:
            self.geolocate()
            print("mapping phop to the site...")
            self.phop_pd['mapped_site'] = self.phop_pd['location'].apply(lambda x:DC_tracer(x))
            self.mapping_dc_lst = self.phop_pd['mapped_site'].value_counts().index.to_list()                         #mapped site
            print(f"In total, using RIPE Atlas can resolve {len(self.mapping_dc_lst)} sites with {len(self.dc_lst)-len(self.mapping_dc_lst)} sites left unresolvable.")
        except Exception as e:
            print(e)
            print("something error when mapping sites")

    def reprePhop(self):         #we want to know which phop is close enough to be unicast representatives
        self.repr_phop = {}
        for _, phop in self.phop_pd.iterrows():
            if phop['location'] != None:
                phop_lat, phop_lon = phop['location'].split('|')[-1].split(',')
                site_lat, site_lon = phop['mapped_site'].split('|')[-1].split(',')
                mapped_site = phop['mapped_site'].split('|')[0]
                if mapped_site not in self.repr_hop:
                    if great_circle((phop_lat, phop_lon),(site_lat,site_lon)).km < 600:
                        self.repr_phop[mapped_site] = [phop.name, great_circle((phop_lat, phop_lon),(site_lat,site_lon)).km]
                else:
                    if great_circle((phop_lat, phop_lon),(site_lat,site_lon)).km < self.repr_phop[mapped_site][1]:
                        self.repr_phop[mapped_site] = [phop.name, great_circle((phop_lat, phop_lon),(site_lat,site_lon)).km]
        print(f"In total, we can find {len(self.repr_phop)} sites' unicast representitives.")

    def geoanalysis(self):          # we want to know how many probes are routed to the closest site geographically
        def siteRank(data):
            dis = great_circle((data["mapped_site"].split("|")[1].split(",")[0], data["mapped_site"].split("|")[1].split(",")[1]), (data['lat'],data['lon'])).km
            rank = 0
            for site in self.mapping_dc_lst:
                if dis < great_circle((site.split("|")[1].split(",")[0], site.split("|")[1].split(",")[1]), (data['lat'],data['lon'])).km:
                    rank += 1
            return rank
        
        "merge"
            #dist = [great_circle((x.split("|")[1].split(",")[0], x.split("|")[1].split(",")[1]), (data['lat'],data['lon'])).km for x in self.mapping_dc_lst]


   # def rttanalysis(self):          # we want to know how many probes are routed to the lowest-latency site