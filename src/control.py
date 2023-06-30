import analysis

if __name__=="main":
    test_analysis = analysis.analysis(dc_name="imperva",target=["45.60.155.44", "45.60.151.44", "45.60.159.44", "45.60.167.44", "45.60.171.44", "45.60.163.44"], mtr_lst=[44104396, 44104397, 44104399, 44104400, 44104401, 44104402, 44104404, 44104405, 44104406, 44104407])                      #analysis to imperva which is encoded in our script
    test_analysis.mapsite()          #mapping each target to the site
    test_analysis.reprePhop()        #find unicast representation
    test_analysis.geoanalysis()      #make geoanalysis
    test_analysis.rttanalysis("../test/imperva/ping_mid.txt")
