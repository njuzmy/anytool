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
```



### Analysis

We have integrated the measurement module into the analysis phase, enabling automatic analysis of the measurement data. You can initiate the analysis phase using any of the following three methods:

* Schedule the measurement using the method mentioned in <a href="#measurement">Measurement</a>.
* Use the built-in measurement by providing the CDN names.
* Provide the measurement IDs.

Additionally, you are also required to provide the site list of the deployments you want to measure, along with their geolocation information. You can place the site list file [here](./dataset/dc_lst), and it should have the same format as the files in the directory.
We also offer site lists for some CDNs such as Cloudflare, Imperva, Akamai, etc. However, please note that these site lists were last updated in June 2023 and are not frequently updated. Therefore, if you want to ensure that your measurements are up-to-date, please provide the latest site lists. To use our provided site lists, you can simply provide the CDN name listed in the [site directory](./dataset/dc_lst)

We provide a two-fold analysis of the measurement data---geolocation and latency. You can 
