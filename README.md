<h1 align="center">
  <br>
   Anytool
  <br>
</h1>
<h4 align="center">A reference implementation of SIGCOMM'23 Paper Regional anycast.</h4>

## 🚀 Key Features: 

> - Measure any kind of anycast deployment.  
> - Several methods are used to process the measurement data.  
> - Analyse the anycast deployment including geographic and network performance.
> - Provide visualized results.  
> - Have the ability to compare anycast deployments used by different CDNs.  

## Get started:

### Requirements

The measurement phase is totally based on **RIPE Atlas**. If you want to customize a new measurement, you will need to provide your RIPE Atlas kays and ensure that you have enough credits to schedule the measurement. If you do not have a RIPE Atlas account or sufficient credits, you can use our built-in measurements. We have conducted measurements for four anycast-based CDNs: Imperva, Edgio, Cloudflare, and Azure. You can check the measurement data and make comparisons using anytool.      

Additionally, the software requirement for our tool is only **Python 3.8.0+**.

There are some dependencies for measurement and analysis functions. To install them.  
```bash
pip install -r ./requrements.txt
```

### Measurement

In the measurement phase, you can customize the measurement to any deployment you want to measure.  

The following content is necessary:  
> - targe: both IP address or hostname are allowed  
> - your RIPE Atlas key(s)

You can also customize the following variant:  
> - the probe list you want to use

If you do not designate the probe list, we will use the [default one](./dataset/srprobe_lst)

```bash
# An example of initializing the measurement
Anytool> get_result -n CDN_NAME -t TARGET -m MEASUREMENT_ID
or
Anytool> get_result -n CDN_NAME -t TARGET -k RIPE_KEY
```

We also provide built-in measurements for researchers:
> imperva-ns
> imperva-cdn
> edgio-ns
> edgio3-cdn
> edgio4-cdn
> cloudflare
> akamai
you can choose any anycast deployment to do further analysis:
```bash
Anytool> built_in
Anytool> choose -n ANYCAST_ID
```
you can also use the "show_result" command to see the complete measurement data:
```bash
Anytool> show_result
```


### Analysis

We have integrated the measurement module into the analysis phase, enabling automatic analysis of the measurement data. You can initiate the analysis phase using any of the following three methods:

* Schedule the measurement using the method mentioned in <a href="#measurement">Measurement</a>.
* Use the built-in measurement by providing the CDN names.
* Provide the measurement IDs.

Additionally, you are also required to provide the site list of the deployments you want to measure, along with their geolocation information. You can place the site list file [here](./dataset/dc_lst), and it should have the same format as the files in the directory.
We also offer site lists for some CDNs such as Cloudflare, Imperva, Akamai, etc. However, please note that these site lists were last updated in June 2023 and are not frequently updated. Therefore, if you want to ensure that your measurements are up-to-date, please provide the latest site lists. To use our provided site lists, you can simply provide the CDN name listed in the [site directory](./dataset/dc_lst)

We provide a two-fold analysis of the measurement data---geolocation and latency. For geolocation analysis, Anytool can tell how many probes are routed to their closest sites. For latency analysis, Anytool will tell how many probes are routed to their lowest-latency sites. Before the analysis, you should first do site mapping and select unicast representatives. For example, when you want to make a geolocation analysis:
```bash
Anytool> map_site
Anytool> geo_analysis
```
Besides, if you want to make a latency analysis:
```bash
Anytool> select_unirepre
Anytool> rtt_analysis
```

## DEMO
We provide a simple DEMO here. Notably, the ability of Anytool is far more plentiful than what DEMO shows.


https://github.com/njuzmy/anytool/assets/38530443/1588df65-93a2-4c44-95e7-70c529f57249




