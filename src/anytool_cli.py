#!/usr/bin/python3
import os
import logging
import time
import traceback
import json
import cmd
import argparse
import analysis

class MainCmd(cmd.Cmd):
    intro = """
----------------------------------------------------
    ___                __              __
   /   |  ____  __  __/ /_____  ____  / /
  / /| | / __ \\/ / / / __/ __ \\/ __ \\/ /
 / ___ |/ / / / /_/ / /_/ /_/ / /_/ / /
/_/  |_/_/ /_/\\__, /\\__/\\____/\\____/_/
             /____/
----------------------------------------------------
    An tool for measuring any kind of anycast deployment.
    """

    prompt = 'Anytool> '

    def __init__(self, config_file='cmu_groups.json'):
        cmd.Cmd.__init__(self)
        self.test_analysis = None

    # TODO
    # def do_analysis(self, arg):
    def do_a(self, arg):
        try:
            self.test_analysis = analysis.analysis(
                dc_name="imperva",
                target=[
                    "45.60.155.44",
                    "45.60.151.44",
                    "45.60.159.44",
                    "45.60.167.44",
                    "45.60.171.44",
                    "45.60.163.44"],
                mtr_lst=[
                    44104396,
                    44104397,
                    44104399,
                    44104400,
                    44104401,
                    44104402,
                    44104404,
                    44104405,
                    44104406,
                    44104407])
            
            print("measure_pd")
            print(self.test_analysis.measure.measure_pd)
        except Exception as e:
            print(e)

    # TODO
    # def do_mapgeo(self,arg):
    def do_m(self,arg):
        try:
            if self.test_analysis is None:
                print("'analysis' first")
                return 
            self.test_analysis.mapsite()
        except Exception as e:
            print(e)
    
    # TODO
    # def do_reprePhop(self,arg):
    def do_r(self,arg):
        try:
            if self.test_analysis is None:
                print("'analysis' first")
                return 
            self.test_analysis.reprePhop()
        except Exception as e:
            print(e)

    # TODO
    # def do_geoanalysis(self,arg):
    def do_g(self,arg):
        try:
            if self.test_analysis is None:
                print("'analysis' first")
                return 
            self.test_analysis.geoanalysis()
        except Exception as e:
            print(e)
    
    # TODO
    # def do_rttanalysis(self.arg):
    def do_rt(self,arg):
        try:
            self.test_analysis.rttanalysis(arg)
        except Exception as e:
            print(e)


    def emptyline(self):
        pass

    def do_EOF(self, line):
        print("")
        return True

    def do_shell(self, line):
        "Run a shell command"
        print("running shell command:", line)
        output = os.popen(line).read()
        print(output)
        self.last_output = output


if __name__ == "__main__":
    MainCmd().cmdloop()
