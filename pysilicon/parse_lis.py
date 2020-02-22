import re
import sys 
import numpy as np
import matplotlib as mpl
from matplotlib import pyplot as plt
from scipy.optimize import curve_fit

# Regex strings
PRE = "TGMkmunpfa"
DEC_SCI = "-?\d+\.?\d*(e[-+]?\d+)?|\.\d+"
DEC_PRE = "-?\d+\.?\d*|\.\d+"
DAT_2_PRE = f"^\s*({DEC_PRE})([{PRE}]?)\s+({DEC_PRE})([{PRE}]?)\s*$"
DAT_2_SCI = f"^\s*({DEC_SCI})\s+({DEC_SCI})\s*$"

# HSPICE prefixes
PREFIX_TRANSLATE = {
    '': 1,
    'T': 1e12,
    'G': 1e9,
    'M': 1e6,
    'k': 1e3,
    'm': 1e-3,
    'u': 1e-6,
    'n': 1e-9,
    'p': 1e-12,
    'f': 1e-15,
    'a': 1e-18
}

#----------------------------------------------------------
# Curve fitting functions
#----------------------------------------------------------
def square_law_func(x,w,l,k,vt):
    ''' 
    k: unCox/2
    vt: threshold voltage
    '''
    return alpha_func(x,w,l,k,vt,2)

def alpha_func(x,w,l,k,vt,a):
    ''' 
    k: unCox/2
    vt: threshold voltage
    a: power
    '''
    return (w/l)*k*np.power(x-vt,a)

def short_channel_func(x,w,l,k,ecl,vt):
    ''' 
    x: Vgs
    w: width 
    l: length 
    k: Ueff*Cox/2
    ecl: Ecrit*length 
    vt: Threshold voltage 
    '''
    return ((w/l)*k*ecl)*(np.power(x-vt,2)/((x-vt)+ecl))

def line_func(x,m,b):
    return m * x + b
#----------------------------------------------------------

#----------------------------------------------------------
# Parsing functions
#----------------------------------------------------------
def get_x_y(line):
    ''' Returns x and r if'''
    m0 = re.search(DAT_2_PRE,line)
    m1 = re.search(DAT_2_SCI,line)
    if m0:
        x = float(m0.group(1)) * PREFIX_TRANSLATE[m0.group(2)]
        y = float(m0.group(3)) * PREFIX_TRANSLATE[m0.group(4)]
        return (x,y)
    elif m1:
        x = float(m1.group(1))
        y = float(m1.group(3))
        return (x,y)

def parse_lis_x_y_ext(fname,*names):
    ''' 
    Simple parsing of lis file 
    :param fname filename path 
    :param names list of data set names (length specifies the number of datasets to be parsed) 
    :return {name: (x,y)} 
    '''
    with open(fname,'r') as fp:
        # Init dictionary, append bool, and names index
        dat = {}
        i = 0
        append = False
        x = []
        y = []
        # Iterate through file
        for line in fp:
            if line == 'y\n':
                dat[names[i]] = (np.asarray(x,dtype=np.float64),np.asarray(y,dtype=np.float64)) 
                i += 1
                if i == len(names):
                    print(f"All datasets found. File: {fname}, Requested: {len(names)}")
                    return dat  
                append = False
                x = []
                y = []
            if append:
                x_y = get_x_y(line) 
                if x_y: 
                    x.append(x_y[0])
                    y.append(x_y[1])
            if line == 'x\n':
                append = True
        # Did not trigger earlier return thus not all datasets were found
        print(f"Warning! Not all requested datasets could be found. File: {fname}, Requested: {len(names)}, Found: {i}")
        return dat 

def parse_lis_x_y(fname):
    ''' Simple parsing of lis file '''
    x = []
    y = []
    with open(fname,'r') as fp:
        append = False
        for line in fp:
            if line == 'y\n':
                append = False
            if append:
                dat = get_x_y(line) 
                if dat: 
                    x.append(dat[0])
                    y.append(dat[1])
            if line == 'x\n':
                append = True
    return (np.asarray(x,dtype=np.float64),np.asarray(y,dtype=np.float64))

def plot_x_y(x,y,ax=None,title='',xlabel='',ylabel='',label=None,xlim=None,ylim=None,show=True):
    if not ax:
        fig,ax = plt.subplots() 
    ax.plot(x,y,'.-',label=label)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if xlim:
        ax.set_xlim(title)
    if ylim:
        ax.set_ylim(title)
    if show:
        plt.show()
    if label:    
        ax.legend()
    return ax

def filter_x_y(x,y,filt=[-np.inf,np.inf]):
    return (x[(x > filt[0]) & (x < filt[1])],y[(x > filt[0]) & (x < filt[1])])
#----------------------------------------------------------

def fit_to_line(x,y,
    bounds=[-np.inf,np.inf],filt=[-np.inf,np.inf],
    title='',xlabel='',ylabel='',xlim=None,ylim=None,fit_num=100
):
    ''' kwargs are for plot_x_y '''
    # Plot original data 
    ax = plot_x_y(x,y,title=title,xlabel=xlabel,ylabel=ylabel,xlim=xlim,ylim=ylim,show=False)
    # Try to filter
    x,y = filter_x_y(x,y,filt=filt)
    # Fit to curve
    popt,pcov = curve_fit(line_func,x,y,bounds=bounds)
    # Generate fit x linspace
    xmin,xmax = ax.get_xlim()
    x_fit = np.linspace(xmin,xmax,num=fit_num)
    # final plot
    return (plot_x_y(x_fit,line_func(x_fit,*popt),
    ax=ax,title=title,xlabel=xlabel,ylabel=ylabel,xlim=xlim,ylim=ylim,show=False),popt,pcov)

def calc_prop_time(time,input_dat,output_dat,title='',xlabel='',ylabel='',plot=False):
    input_i = index_closest_to(input_dat,(input_dat[0]+input_dat[-1])/2)
    output_i = index_closest_to(output_dat,(output_dat[0]+output_dat[-1])/2)
    tp_s = time[input_i]
    tp_e = time[output_i]
    if plot:
        ax = plot_x_y(time,input_dat,label="Input",show=False)
        plot_x_y(time,output_dat,
            label="Output",title=title,xlabel=xlabel,ylabel=ylabel,ax=ax,show=False)
        ylim = ax.get_ylim()
        ax.plot([tp_s,tp_s],ylim,'k')
        ax.plot([tp_e,tp_e],ylim,'k')
        ax.legend()
    return (tp_s,tp_e,tp_e-tp_s)

def index_closest_to(array,value):
    array_diff = np.abs(array - value)
    return array_diff.argmin()
