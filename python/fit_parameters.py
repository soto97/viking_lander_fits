#!/usr/bin/env python
#Christopher Lee, Ashima Research, 2013
import numpy
import argparse
from scipy import optimize, linalg
from fit_core import *

def find_delta_x(data, basename):
    base = data[basename]
    dn = base.keys()
    excluded = ["filename", "data"]
    parameter_names = list(set(dn).difference(set(excluded)))
    
    for k,v in data.items():
        #skip if this entry is the baseline entry
        if k==basename:
            continue
        #iterate over parameters to find the delta
        delta = dict([(pn, v[pn]-base[pn]) for pn in parameter_names])
        #how many are non zero
        nonzero=0
        for pn,vn in delta.items():
            if abs(vn) > 1e-10:
                nonzero+=1
                result=vn
                result_name=pn
        if nonzero>1:
            print "Error, found too many non-zeroes perturbations"
        v["deltax"]=result
        v["deltax_name"]=result_name
        #now delta p
        v["data"]["delta_p_vl1"] = v["data"]["vl1"] - base["data"]["vl1"]
        v["data"]["delta_p_vl2"] = v["data"]["vl2"] - base["data"]["vl2"]
        v["data"]["delta_f_vl1"] = v["data"]["p1"]  - base["data"]["p1"]
        v["data"]["delta_f_vl2"] = v["data"]["p2"]  - base["data"]["p1"]
    return data

def fit_parameters(parameter_file, viking, lander="vl1", delimiter=","):
    
    data, basename = load_files(parameter_file, delimiter=delimiter)
    viking_data = read_file(viking, delimiter=delimiter)
    
    ls = numpy.arange(360)

    for k,v in data.items():
        d=v["data"]
        #regenerate the L_S dependent data
        d["L_S"] = ls
        d["vl1"] = fitfunc(d["p1"], d["L_S"])
        d["vl2"] = fitfunc(d["p2"], d["L_S"])

    viking_data["L_S"] = ls
    viking_data["vl1"] = fitfunc(viking_data["p1"], viking_data["L_S"])
    viking_data["vl2"] = fitfunc(viking_data["p2"], viking_data["L_S"])

    #calculate perturbations
    dp = []
    dx = []
    dp2= []
    find_delta_x(data, basename)
        
    base = data.pop(basename)
    
    delta = viking_data[lander] - base["data"][lander]
    name=[]
    for key, val in data.items():
        dp.append( val["data"]["delta_p_vl1".format(lander)] )
        dp2.append( val["data"]["delta_p_vl2".format(lander)] )
        dx.append( val["deltax"] )
        name.append(key)


    a2=numpy.array([p/x for p,x in zip(dp, dx)]).T
    a1=numpy.array([p/x for p,x in zip(dp2, dx)]).T

    a=dict(vl1=a1, vl2=a2)
    X = linalg.lstsq(a[lander], #A,
                     delta) # B)
    vl1 = numpy.zeros(len(base["data"]["L_S"])) + base["data"]["vl1"]
    vl2 = numpy.zeros(len(base["data"]["L_S"])) + base["data"]["vl2"]
    
    for s, p1,p2 in zip(X[0], a["vl1"].T,a["vl2"].T ): 
        vl1 = vl1 + s * p1
        vl2 = vl2 + s * p2
        
    base["data"]["fit_vl1"]=vl1
    base["data"]["fit_vl2"]=vl2
    base["data"]["res_vl1"]=viking_data["vl1"]-vl1
    base["data"]["res_vl2"]=viking_data["vl2"]-vl2

    return data, base, X
    
if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("parameter_file", type=str)
    parser.add_argument("viking", type=str)
    parser.add_argument("output_filename_parameters", type=str)
    parser.add_argument("output_filename_fit", type=str)
    parser.add_argument("--delimiter", type=str, default=',')
    parser.add_argument("--lander_name", type=str, default="vl1")

    args = parser.parse_args()

    data,base,X = fit_parameters(args.parameter_file, args.viking,lander=args.lander_name, delimiter=args.delimiter)
    
    result=dict()
    result["names"] = [data[n]["deltax_name"] for n in data]
    result["basevalue"] = [base[data[n]["deltax_name"]] for n in data]
    result["perturbation"] = [x for x in X[0]]
    result["newvalue"] = [a+b for a,b in zip(result["basevalue"],result["perturbation"])]

    target = open(args.output_filename_parameters, 'w')
    target.write("#Parameter fit to best reproduce {0} data\n".format(args.lander_name))
    
#   Fit to VL data from {0} with {1} harmonic modes\n".format(args.input_filename, args.nmodes))
    asciitable.write(result,target, delimiter=args.delimiter, 
                    names=["names","basevalue","perturbation","newvalue"], 
                    formats=dict(perturbation="%.4f", newvalue="%.4f"))
    
    target.close()
    
    #print base["data"].keys()
    result2 = dict(L_S=base["data"]["L_S"], 
                    vl1=base["data"]["fit_vl1"], 
                    vl2=base["data"]["fit_vl2"],
                    res_vl1=base["data"]["res_vl1"], 
                    res_vl2=base["data"]["res_vl2"],
                    )
    
    target2 = open(args.output_filename_fit, 'w')
    target2.write("#Best fit pressure curve to {0} data\n".format(args.lander_name))
    for line in open(args.output_filename_parameters):
        target2.write("#"+line)
    asciitable.write(result2,target2, delimiter=args.delimiter, 
                    names=["L_S","vl1","vl2", "res_vl1","res_vl2"])
    
    target2.close()