import numpy as np
from labjack import ljm
from .channels import StreamChannel

''' Setup a periodic stream on a single output channel.

Similar to a standard stream, using an ljm call that handles looping and simplifies setup.

https://support.labjack.com/docs/periodicstreamout-ljm-user-s-guide

First .configure to set rate.
.add(data, target, buffer_index) for up to 4 streams (buffers 0:3)
Start streaming with .start(), stop with .stop()

NOTE: PeriodicStreamOut set STREAM_OUT#(0:3)_BUFFER_ALLOCATE_NUM_BYTES to 16384.

NOTE: The following registers are configurated automatically and SHOULD NOT be updated manually!
STREAM_OUT#(0:3)_TARGET
STREAM_OUT#(0:3)_BUFFER_ALLOCATE_NUM_BYTES
STREAM_OUT#(0:3)_LOOP_NUM_VALUES
STREAM_OUT#(0:3)_ENABLE
STREAM_OUT#(0:3)_BUFFER_U16
STREAM_OUT#(0:3)_SET_LOOP


'''


class WaveformGenerator:
    def __init__(self, labjack, ):
        self.labjack = labjack
        self.scan_list = []
        self.scan_rate = 0
        self.scans_per_read = 1


    def configure(self, scan_rate:int, scans_per_read:int = 2):
        self.scan_rate = scan_rate
        self.scans_per_read = scans_per_read


    def add(self, data:list, target:StreamChannel|str, stream_out_index:int = 0):
        ''' 
        Setup a periodic output stream on output device 'target' using buffer stream_out_index.

        LJM_PeriodicStreamOut(
            int Handle,
            int StreamOutIndex,
            int TargetAddr,
            double ScanRate,
            int NumValues,
            const double * aWriteData)
        '''

        self.stream_out_index = stream_out_index

        target_addr = ljm.nameToAddress(target)[0]
        scan_addr   = ljm.nameToAddress(f'STREAM_OUT{stream_out_index}')[0]
        self.scan_list.append(scan_addr)

        if (self.scan_rate <= 0) or (self.scan_rate > self._device_scanRate()*len(self.scan_list)):
            print(f'WARNING: ScanRate {self.scan_rate} for {len(self.scan_list)} channels is invalid')

        ljm.periodicStreamOut(
            handle         = self.labjack.handle,
            streamOutIndex = stream_out_index,
            targetAddr     = target_addr,
            scanRate       = self.scan_rate,
            numValues      = len(data),
            aWriteData     = data
        ) 
        return
    

    def add_many(self, data:list[list], targets:list[StreamChannel|str], stream_out_indexes:list[int]):
        if (len(data) != len(targets)) or (len(data) != len(stream_out_indexes)):
            raise ValueError("Length of data, targets, and stream_out_indexes must match")
        for d, t, i in zip(data, targets, stream_out_indexes):
            self.add(d, t, i)
        return
    

    def start(self):
        self.stop()
        ljm.eStreamStart(
            handle = self.labjack.handle,
            scansPerRead = self.scan_rate // self.scans_per_read,
            numAddresses = len(self.scan_list),
            aScanList = self.scan_list,
            scanRate = self.scan_rate
        )
        return
    
    
    def stop(self):
        ''' Stop streaming if currently running '''
        try:
            ljm.eStreamStop(self.labjack.handle)
        except:
            pass
        return

    #TODO Refactor this to core
    def _device_scanRate(self) -> int:
        if self.labjack.device_type == ljm.constants.dtT7:
            return 100000
        else:
            raise ValueError("Only labjack T7 supported")


