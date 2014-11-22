#!/usr/bin/env python
from libgoods import utools, nctools, data_files_dir
import datetime as dt
import os 

'''
Sample script to retrieve data from unstructured grid netcdf "file" (can be
OPeNDAP url), generate necessary grid topology (boundary info), and write 
GNOME compatible output.

The boundary file is saved to the data files directory so it only needs 
to be generated once (unless you are subsetting the grid).

To process multiple files (urls) either
a) pass the filenames/urls in as a list -- this creates a netcdf4 MFDataset and is
a good option for not too many files (all output is written to one nc file for GNOME 
in this case)
b) add a file list loop -- in this case put it after the grid topo vars are loaded (as
this only has to be done once). See NGOFS_multifile_example.py

'''

# specify local file or opendap url
#data_url = 'http://opendap.co-ops.nos.noaa.gov/thredds/dodsC/NOAA/NGOFS/MODELS/201309/nos.ngofs.fields.f000.20130901.t03z.nc'
sdate = dt.datetime(2014,3,21,0,0)
edate = dt.datetime(2014,3,25,0,0)

flist = []
url_stem = 'http://opendap.co-ops.nos.noaa.gov/thredds/dodsC/NOAA/NGOFS/MODELS/'
while sdate < edate:
    yr = str(sdate.year)
    mon = str(sdate.month).zfill(2)
    day = str(sdate.day).zfill(2)
    hr = str(sdate.hour).zfill(2)
    url_sub_dir = yr + mon
    fname = 'nos.ngofs.fields.nowcast.' + yr + mon + day + '.t' + hr + 'z.nc'
    flist.append(url_stem + url_sub_dir + '/' + fname)
    delta_t = dt.timedelta(0.25,0)
    sdate = sdate + delta_t
    
# the utools class requires a mapping of specific model variable names (values)
# to common names (keys) so that the class methods can work with FVCOM, SELFE,
# and ADCIRC which have different variable names
# (This seemed easier than finding them by CF long_names etc)
var_map = { 'longitude':'lon', \
            'latitude':'lat', \
            'time':'time', \
            'u_velocity':'u', \
            'v_velocity':'v', \
            'nodes_surrounding_ele':'nv',\
            'eles_surrounding_ele':'nbe',\
          }  

for file in flist:
    
    print file
    
    # class instantiation creates a netCDF Dataset object as an attribute
    ngofs = utools.ugrid(file)
    
    # get longitude, latitude, and time variables
    print 'Downloading data dimensions'
    ngofs.get_dimensions(var_map)
    
    #display available time range for model output
    nctools.show_tbounds(ngofs.Dataset.variables['time'])
    
    # get grid topo variables (nbe, nv)
    print 'Downloading grid topo variables'
    ngofs.get_grid_topo(var_map)
    # GNOME needs to know whether the elements are ordered clockwise (FVCOM) or counter-clockwise (SELFE)
    ngofs.atts['nbe']['order'] = 'cw'
    
    #subsetting
    print 'Subsetting'
    nl = 29.7; sl = 28.1
    wl = -96.9; el = -94.1
    
    # Find all nodes and complete elements in subset box, lat/lon subset variables
    ngofs.find_nodes_eles_in_ss(nl,sl,wl,el)
    
    # GNOME requires boundary info -- this file can be read form data_files directory
    # if already generated (!!!for this particular subset!!!)
    # Find subset boundary -- if any of the subset boundary segments correspond to segments
    # in the full domain boundary then use boundary type info -- otherwise assume its 
    # an open water boundary (then write this new subset boundary to a file)
    ss_bndry_file = os.path.join(data_files_dir, 'ngofs_gb.bry')
    try:
        ngofs.read_bndry_file(ss_bndry_file)
        print 'Read previously generated boundary file'
    except IOError:
        print 'Creating boundary file'
        bndry_file = os.path.join(data_files_dir, 'ngofs.bry') #already exists (no check!)
        ngofs.ss_land_bry_segs = ngofs.remap_bry_nodes(bndry_file)
        ngofs.write_bndry_file('subset',ss_bndry_file)
        ngofs.read_bndry_file(ss_bndry_file)
    # Download u/v -- this is done in multiple OPeNDAP calls of contiguous data blocks
    print 'Downloading data'
    ngofs.get_data(var_map,nindex=ngofs.nodes_in_ss) #All time steps in file (i.e. tindex=None)
      
    print 'Writing to GNOME file'
    ofn = file.split('nowcast.')[-1]
    print ofn
    ngofs.write_unstruc_grid(os.path.join(data_files_dir, ofn))