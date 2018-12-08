import pytest
import requests
import os
import time
import random
import urllib
import astropy.io.fits as fits

import ddosaclient

test_scw=os.environ.get('TEST_SCW',"010200210010.001")
test_scw_list_str=os.environ.get('TEST_SCW_LIST','["005100410010.001","005100420010.001","005100430010.001"]')
                                    
default_callback="http://mock-dispatcher.dev:6001/callback"

def test_mosaic_delegation_cat_distribute():
    remote=ddosaclient.AutoRemoteDDOSA()

    random_ra=83+(random.random()-0.5)*5
    cat = ['SourceCatalog',
           {
               "catalog": [
                   {
                       "DEC": 23,
                       "NAME": "TEST_SOURCE1",
                       "RA": 83
                   },
                   {
                       "DEC": 13,
                       "NAME": "TEST_SOURCE2",
                       "RA": random_ra
                   }
               ],
               "version": "v1"
           }
        ]


    job_id=time.strftime("%y%m%d_%H%M%S")
    encoded=urllib.urlencode(dict(job_id=job_id,session_id="test_mosaic"))

    print("encoded:",encoded)

    custom_version = "imgbins_for_"+job_id
        
    kwargs = dict(target="mosaic_ii_skyimage",
                           modules=["git://ddosa", 'git://rangequery','git://gencat/dev','git://ddosa_delegate'],
                           assume=['ddosa.ImageGroups(input_scwlist=rangequery.TimeDirectionScWList)',
                                   'rangequery.TimeDirectionScWList(\
                                         use_coordinates=dict(RA=83,DEC=22,radius=5),\
                                         use_timespan=dict(T1="2014-04-12T11:11:11",T2="2015-04-12T11:11:11"),\
                                         use_max_pointings=%i \
                                    )'%int(os.environ.get("TEST_N_POINTINGS",3)),
                                   'ddosa.ImageBins(use_ebins=[(20,80)],use_autoversion=False, use_version="%s")'%custom_version,
                                   'ddosa.ImagingConfig(use_SouFit=0,use_version="soufit0")'],
                           callback=default_callback+"?"+encoded,
                           prompt_delegate=True,
                           inject=[cat],
                         )

    with pytest.raises(ddosaclient.AnalysisDelegatedException) as excinfo:
        product = remote.query(**kwargs)
        # callback="http://intggcn01:5000/callback?job_id=1&asdsd=2",

    assert excinfo.value.delegation_state == "submitted"

    while True:
        time.sleep(5)
    
        try:
            product = remote.query(**kwargs)
        except ddosaclient.AnalysisDelegatedException as e:
            print("state:",e.delegation_state)
        else:
            print("DONE:",product)
            break

    assert hasattr(product,'skyima')
    assert hasattr(product,'skyres')
    assert hasattr(product,'srclres')

    sr = fits.open(product.srclres)[1].data

    print(sr)

    assert 'NEW_1' in sr['NAME']
    assert 'TEST_SOURCE1' in sr['NAME']
        


def test_mosaic_delegation_failing():
    remote=ddosaclient.AutoRemoteDDOSA()

    job_id=time.strftime("%y%m%d_%H%M%S")
    encoded=urllib.urlencode(dict(job_id=job_id,session_id="test_mosaic"))

    print("encoded:",encoded)

    custom_version = "imgbins_for_"+job_id
        
    kwargs = dict(target="mosaic_ii_skyimage",
                           modules=["git://ddosa", 'git://rangequery','git://ddosa_delegate'],
                           assume=['ddosa.ImageGroups(input_scwlist=rangequery.TimeDirectionScWList)',
                                   'rangequery.TimeDirectionScWList(\
                                         use_coordinates=dict(RA=83,DEC=22,radius=5),\
                                         use_timespan=dict(T1="2014-04-12T11:11:11",T2="2015-04-12T11:11:11"),\
                                         use_max_pointings=%i \
                                    )'%int(os.environ.get("TEST_N_POINTINGS",3)),
                                   'ddosa.ghost_bustersImage(input_fail=ddosa.FailingMedia)',
                                   'ddosa.ImageBins(use_ebins=[(20,80)],use_autoversion=False, use_version="%s")'%custom_version,
                                   'ddosa.ImagingConfig(use_SouFit=0,use_version="soufit0")'],
                           callback=default_callback+"?"+encoded,
                           prompt_delegate=True,
                         )

    with pytest.raises(ddosaclient.AnalysisDelegatedException) as excinfo:
        product = remote.query(**kwargs)
        # callback="http://intggcn01:5000/callback?job_id=1&asdsd=2",

    assert excinfo.value.delegation_state == "submitted"

    while True:
        time.sleep(5)
    
        try:
            product = remote.query(**kwargs)
        except ddosaclient.AnalysisDelegatedException as e:
            print("state:",e.delegation_state)
        except ddosaclient.WorkerException:
            print("worker exception:",e.__class__)
            break
        except Exception as e:
            print("undefined failure:",e.__class__,e)
            raise
        else:
            print("DONE:",product)
            break

