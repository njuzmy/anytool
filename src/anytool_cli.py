#!/usr/bin/python3
import os
import logging
import time
import traceback
import json
import cmd
import argparse
import analysis
import pickle
import pandas as pd


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

    def __init__(self):
        cmd.Cmd.__init__(self)
        self.test_analysis = None
        self.aliases = {'a': self.do_get_result,
                        'show': self.do_show_result,
                        'save': self.do_save_result,
                        'm': self.do_map_site,
                        'r': self.do_select_unirepre,
                        'g': self.do_geo_analyze,
                        'rt': self.do_rtt_analyze}

    def do_get_result(self, arg):
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

            #print("measure_pd")
            #print(self.test_analysis.measure.measure_pd)
        except Exception as e:
            print(e)

    def do_show_result(self, arg):
        try:
            if self.test_analysis is None:
                print("Please get the results first")
                return
            print(self.test_analysis.measure.measure_pd)
        except Exception as e:
            print(e)

    def do_save_result(self, arg):
        parser = argparse.ArgumentParser()
        parser.add_argument("-l", "--location", dest="location", type=str, default="../dataset/a.csv", help="where to save the result")
        try:
            args = parser.parse_args(arg.split())
            if args is None:
                print("Please specify the save location")
            if self.test_analysis is None:
                print("Please get the results first")
                return
            self.test_analysis.measure.measure_pd.to_csv(args.location)
            #self.test_analysis.measure.measure_pd
        except Exception as e:
            print(e)

    def do_map_site(self, arg):
        try:
            if self.test_analysis is None:
                print("Please get the results first")
                return
            self.test_analysis.mapsite()
        except Exception as e:
            print(e)

    def do_select_unirepre(self, arg):
        try:
            if self.test_analysis is None:
                print("'analysis' first")
                return
            self.test_analysis.reprePhop()
        except Exception as e:
            print(e)

    def do_geo_analyze(self, arg):
        try:
            if self.test_analysis is None:
                print("'analysis' first")
                return
            self.test_analysis.geoanalysis()
            with open("temp.pkl", "wb") as f:
                pickle.dump(self.test_analysis, f)
        except Exception as e:
            print(e)

    def do_rtt_analyze(self, arg):
        try:
            try:
                with open("temp.pkl", "rb") as f:
                    self.test_analysis = pickle.load(f)
            except BaseException:
                pass
            if self.test_analysis is None:
                print("'analysis' first")
                return
            arg = "../test/imperva/ping_mid.txt"
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

    def default(self, line):
        cmd, arg, line = self.parseline(line)
        if cmd in self.aliases:
            self.aliases[cmd](arg)
        else:
            print("*** Unknown syntax: %s" % line)


if __name__ == "__main__":
    MainCmd().cmdloop()
