#!/usr/bin/env python

#
#  dewadl
#
#   Turn WADL XML into Python API.
#
#   Matt Kubilus 2015
#
#   This is written to support the uDeploy WADL specifically.  Your mileage may vary with other WADLs.
#
#


import os
import re
import cmd
import json
import urlparse
import urllib2
from types import FunctionType
import xml.etree.ElementTree as ET
from functools import partial
from optparse import OptionParser
import ConfigParser
import pprint
import getpass

DEBUG=False

class wadl_processor(object):
    ns={"ns":"http://wadl.dev.java.net/2009/02"}
    base_url = ""

    def __init__(self, wadl_file=None, wadl_url=None, userid=None, passwd=None):

        if wadl_url:
            # If we were supplied wadl_url, first we may need to authenticate in order to get the WADL file 
            self.__auth(wadl_url, userid, passwd)
            wadl_string = self.__do_url(wadl_url)
            self.__process_wadl(wadl_file=wadl_file, wadl_string=wadl_string)
        else:
            # If we have a supplied wadl_file, we will need to get the base_url from the file before auth
            self.__process_wadl(wadl_file=wadl_file)
            self.__auth(self.base_url, userid, passwd)


    def __auth(self, url, userid=None, passwd=None):
        if userid:
            if not passwd:
                passwd = getpass.getpass()

            p = urlparse.urlparse(url)
            auth_url = "%s://%s" % (p.scheme, p.netloc)

            print "Authenticating to %s" % auth_url
            
            connected = False
            for i in range(5):
                try:
                    p_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
                    p_mgr.add_password(None, auth_url, userid, passwd)
                    auth_handler = urllib2.HTTPBasicAuthHandler(p_mgr)
                    opener = urllib2.build_opener(auth_handler)
                    urllib2.install_opener(opener)
                except urllib2.URLError:
                    print "Error connecting"
                    time.sleep(i)
                    continue
                connected = True
                print "Successfully authenticated."
                break 
            
            if not connected:
                print "Could not connect to: %s" % url
                sys.exit(1)


    def __do_url(self, url, mtype="GET", data_dict=None):
        myurl = "/".join(x.strip('/') for x in [self.base_url, url])
        myurl = myurl.lstrip("/")
        req = urllib2.Request(myurl, json.dumps(data_dict))
        req.get_method = lambda: mtype
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError, err:
            print "Error %sting url: %s" % (mtype, myurl)
            print err
            return

        con_type = response.info().getheader('Content-Type')
        resp_data = response.read()

        if resp_data and "application/json" in con_type :
            #return json.loads(resp_data)
            return json.loads(resp_data, object_hook=wadl_to_obj)
        elif resp_data:
            return resp_data

    def __method_creator(cls, url, mtype, params):
        if DEBUG:
            print "Creating method: ", url, mtype, params 

        def method_template(*args, **kwds):
            data_dict = kwds.get("data_dict")
            if DEBUG:
                print "PARAMS:", params
                print "ARGS:", args
                print "KWDS:", kwds
                print "URL:", url
                print "DATADICT:", data_dict

            arglen = len(args)
            m = re.findall("{(.*?)}", url)
            if arglen != len(params):
                print "Requires %s arguments(s) %s" % (len(params), params)
                return 

            do_url = url

            #for idx in xrange(arglen):
            for idx in xrange(len(m)):
                # First replace REST positional arguments
                do_url = do_url.replace("{%s}" % m[idx], args[idx])
               
            url_args = '&'.join([ "%s=%s" % (k,v) for k,v in zip(params[len(m):],args[len(m):])])

            do_url = do_url.replace("//","/")    
            if url_args:
                do_url = "%s?%s" % (do_url, url_args)

            return cls.__do_url(do_url, mtype, data_dict=data_dict)

        return method_template

    def __handleResources(self, resources):
        if DEBUG:
            print resources
        self.base_url = resources.get("base")
        print "Setting base_url to: %s" % self.base_url
        for resource in resources:
            self.__handleResource(resource)

    def __handleResource(self, resource, path=""):
        if DEBUG:
            print "resource", resource.tag, resource.get('path')
        prev_path = path
        path = '/'.join([path, resource.get('path')])
        params = re.findall("{(.*?)}", path)
        method=None
        for node in resource:
            # We have to assume params come before methods
            if node.tag == "{%s}method" % self.ns.get('ns'):
                mtype, method, method_params = self.__handleMethod(node, path)

                if hasattr(self, method):
                    # We have clashed with an existing method name

                    # TODO: After we process the entire file, perhaps cleanup original clashed name
                    basename = os.path.basename(prev_path)
                    if DEBUG:
                        print "RESOURCE: ", prev_path
                        print "Method %s already exists.  Adjusting name to %s" % (method, "%s_%s" % (basename, method))
                        
                    old_method_t = getattr(self, method)
                    method = "%s_%s" % (basename, method)
                    old_method_name = "%s_%s" % (os.path.basename(old_method_t.__prev_path), old_method_t.__name__)
                    if DEBUG:
                        print "Also updating %s to %s" %  (old_method_t.__name__, old_method_name) 
                    setattr(self, old_method_name, old_method_t)

                params.extend(method_params)
                #print "Create method for %s" % path
                tmethod = self.__method_creator(path, mtype, tuple(params))
                tmethod.__doc__ = "%s accepts arguments: %s" % (method, params)
                tmethod.__name__ = method
                tmethod.__prev_path = prev_path
                setattr(self, method, tmethod)
                #params = []
            if node.tag == "{%s}param" % self.ns.get('ns'):
                param = self.__handleParam(node, path)
                #params.append(param)
            if node.tag == "{%s}resource" % self.ns.get('ns'):
                self.__handleResource(node, path)

    def __handleRequest(self, request):
        if DEBUG:
            print "    ", request.tag
        
        tparams = []
        for node in request:
            if node.tag == "{%s}param" % self.ns.get('ns'):
                param = self.__handleParam(node, "")
                if param:
                    tparams.append(param)

        return tparams
        
    def __handleResponse(self, response):
        pass

    def __handleMethod(self, method, path):
        if DEBUG:
            print "  ", method.tag, method.get('id')

        method_type = method.get('name')
        method_name = method.get('id')
        method_params = []
        
        for node in method:
            if node.tag == "{%s}request" % self.ns.get('ns'):
                tparams = self.__handleRequest(node)
                method_params.extend(tparams)
            elif node.tag == "{%s}response" % self.ns.get('ns'):
                self.__handleResponse(node)    
                    
        return method_type, method_name, method_params

    def __handleParam(self, param, path):
        if DEBUG:
            print "  ", param.tag, param.get('name'), param.get('type'), param.get('style')
        
        p = None
        if param.get('style') == 'template':
            p = param.get('name')
        return p

    def __process_wadl(self, wadl_file=None, wadl_string=None):
        if wadl_file:
            tree = ET.parse(wadl_file)
            root = tree.getroot()
        elif wadl_string:
            root = ET.fromstring(wadl_string)
        else:
            print "Must provide either wadl_file or wadl_string"
            return 1

        #print root.tag

        m = re.match("\{(.*)\}application", root.tag)
        if m:
            self.ns['ns'] = m.groups()[0]
            #print "Setting namespace to: %s" % self.ns.get('ns')

        for resources in root.findall('{%s}resources' % self.ns.get('ns')):
            self.__handleResources(resources)
        print "Done processing wadl"


def call_method(obj, args):
    if len(args) >= 1:
        meth_name = args[0]
    else:
        meth_name = "help"
        
    if args > 1:
        params = args[1:]
            
    meths = [method for method in dir(obj) if callable(getattr(obj, method)) and not method.startswith('__')]

    if meth_name == "help":
        print "------------------"
        print "Available methods:"
        print "------------------"
        for meth in meths:
            print meth,
            do_method = getattr(obj, meth)
            argc = do_method.func_code.co_argcount
            print do_method.func_code.co_varnames[1:argc]
            print "    ", do_method.__doc__
            print
        return

    if meth_name in meths:
        do_method = getattr(obj, meth_name)
        return do_method(*params)
    else:
        print "Could not find: %s", meth_name

def wadl_to_obj(d):
    tmpobj = _wadl_obj(d)
    return tmpobj

class _wadl_obj(dict):
    def __init__(self, data):
        for key, value in data.iteritems():
            setattr(self, key, value)
            self.__dict__[key] = value

    def __setattr__(self, name, value):
        if not hasattr(super(_wadl_obj, self), name):
            super(_wadl_obj, self).__setitem__(name, value)

def get_config():
    config = ConfigParser.ConfigParser()
    config.read([".dewadl", "/etc/dewadl.cfg", os.path.expanduser("~/.dewadl")])

    #print config._sections    
    all_defaults = config._sections
    return all_defaults.get("dewadl", {})


if __name__ == "__main__":
   
    cfg_defaults = get_config()
    
    parser = OptionParser()
    parser.add_option(
        "-f",
        "--wadlfile",
        action="store",
        dest="wadlfile",
        default=None
    )
    parser.add_option(
        "-w",
        "--weburl",
        action="store",
        dest="weburl",
        default=cfg_defaults.get("weburl")
    )
    parser.add_option(
        "-u",
        "--userid",
        action="store",
        dest="userid",
        default=cfg_defaults.get("userid")
    )
    parser.add_option(
        "-p",
        "--password",
        action="store",
        dest="password",
        default=cfg_defaults.get("password")
    )
    parser.add_option(
        "-i",
        "--interact",
        action="store_true",
        dest="interact",
        default=False
    )

    opts, args = parser.parse_args()

    if opts.wadlfile:
        wadl = wadl_processor(wadl_file=opts.wadlfile, userid=opts.userid, passwd=opts.password)
    elif opts.weburl:
        wadl = wadl_processor(wadl_url=opts.weburl, userid=opts.userid, passwd=opts.password)
    else:
        parser.error("Please provider either --wadlfile or --weburl")

    if opts.interact:
        import rlcompleter
        import readline
        import code
        import sys
        readline.parse_and_bind('tab: complete')
        sys.ps1 = "W) "
        sys.ps2 = ". "
        vars = globals().copy()
        vars.update(locals())
        shell = code.InteractiveConsole(vars)
        shell.interact(banner="\n\n-----------------------------\n\nWelcome to DeWADL Python interface!.\n'wadl' object has been created.\n")
        sys.exit(0)

    ret = call_method(wadl, args)
    if ret:
        pprint.pprint(ret)
